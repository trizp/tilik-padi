"""Unit test modul inti: pembacaan foto, aturan tingkat, pra-/pasca-proses, dan inferensi ONNX."""
import csv
import hashlib
import io

import numpy as np
import pytest
from PIL import Image

from conftest import PROYEK, VAL, butuh_data
from core import diagnosis as dg
from core import gambar, inferensi


def jpeg(w=200, h=100, warna=(40, 120, 60), exif_orientasi=None):
    im = Image.new("RGB", (w, h), warna)
    buf = io.BytesIO()
    if exif_orientasi:
        ex = Image.Exif()
        ex[0x0112] = exif_orientasi
        im.save(buf, "JPEG", exif=ex.tobytes())
    else:
        im.save(buf, "JPEG")
    return buf.getvalue()


# ---------- pembacaan foto
def test_tolak_bukan_gambar():
    with pytest.raises(gambar.FotoDitolak, match="bukan foto"):
        gambar.baca_foto(b"ini teks, bukan foto")


def test_tolak_kosong_dan_terlalu_besar():
    with pytest.raises(gambar.FotoDitolak, match="kosong"):
        gambar.baca_foto(b"")
    with pytest.raises(gambar.FotoDitolak, match="lebih dari batas"):
        gambar.baca_foto(b"\xff" * (10 * 1024 * 1024 + 1), 10)


def test_tolak_terlalu_kecil_dan_format_lain():
    with pytest.raises(gambar.FotoDitolak, match="terlalu kecil"):
        gambar.baca_foto(jpeg(20, 20))
    buf = io.BytesIO()
    Image.new("RGB", (100, 100)).save(buf, "GIF")
    with pytest.raises(gambar.FotoDitolak, match="tidak didukung"):
        gambar.baca_foto(buf.getvalue())


def test_png_rgba_menjadi_rgb():
    buf = io.BytesIO()
    Image.new("RGBA", (64, 48), (10, 20, 30, 128)).save(buf, "PNG")
    im = gambar.baca_foto(buf.getvalue())
    assert im.mode == "RGB" and im.size == (64, 48)


def test_koreksi_orientasi_exif():
    im = gambar.baca_foto(jpeg(200, 100, exif_orientasi=6))      # 6 = putar 90 derajat
    assert im.size == (100, 200)


# ---------- aturan tingkat
@pytest.mark.parametrize("k,t", [(0.35, "terdeteksi"), (0.3499, "kemungkinan"), (0.29, "kemungkinan"), (0.2899, "tidak_terdeteksi"),
                                 (0.0, "tidak_terdeteksi"), (1.0, "terdeteksi")])
def test_tingkat_batas(k, t):
    assert dg.tentukan_tingkat(k, 0.35, 0.29) == t


def test_diagnosis_kotak_teratas_dan_tanpa_kotak():
    K = inferensi.Kotak
    kelas = ("leaf_blast", "brown_spot", "bacterial_leaf_blight")
    h = dg.diagnosis([K(0, 0, 1, 1, 0.30, 1), K(0, 0, 1, 1, 0.62, 0), K(2, 2, 3, 3, 0.31, 0)], kelas, 0.35, 0.29)
    assert (h.penyakit, h.tingkat, h.keyakinan) == ("leaf_blast", "terdeteksi", 0.62)
    assert len(dg.kotak_untuk_digambar(h, kelas, 0.29)) == 2       # hanya kelas diagnosis dan >= 0,29
    h0 = dg.diagnosis([], kelas, 0.35, 0.29)
    assert (h0.penyakit, h0.tingkat, h0.keyakinan) == (None, "tidak_terdeteksi", 0.0)
    assert dg.kotak_untuk_digambar(h0, kelas, 0.29) == []


# ---------- pra-proses dan pasca-proses
def test_letterbox_persegi_panjang():
    img = np.zeros((480, 640, 3), np.uint8)
    lb, r, (kiri, atas) = inferensi.letterbox(img, 640)
    assert lb.shape == (640, 640, 3) and r == 1.0 and (kiri, atas) == (0, 80)
    assert (lb[:80] == 114).all() and (lb[-80:] == 114).all()


def test_letterbox_potret_besar():
    img = np.zeros((4000, 3000, 3), np.uint8)
    lb, r, (kiri, atas) = inferensi.letterbox(img, 640)
    assert lb.shape == (640, 640, 3) and r == pytest.approx(0.16) and (kiri, atas) == (80, 0)


def test_bilinear_identitas_dan_rata():
    img = np.random.default_rng(0).integers(0, 255, (50, 70, 3), dtype=np.uint8)
    assert np.array_equal(inferensi.ubah_ukuran_bilinear(img, 70, 50), img)
    rata = np.full((40, 40, 3), 77, np.uint8)
    assert (inferensi.ubah_ukuran_bilinear(rata, 17, 23) == 77).all()


def test_nms_per_kelas():
    kotak = np.array([[0, 0, 10, 10], [0.5, 0.5, 10.5, 10.5], [100, 100, 110, 110]], np.float32)   # IoU kotak 0-1 = 0,82
    skor = np.array([0.9, 0.8, 0.7], np.float32)
    assert list(inferensi.nms(kotak, skor, 0.7)) == [0, 2]
    # kelas berbeda tidak saling menekan karena offset 7680
    k2 = kotak.copy()
    k2[1] += 7680
    assert list(inferensi.nms(k2, skor, 0.7)) == [0, 1, 2]


def test_pasca_proses_koordinat():
    out = np.zeros((1, 7, 4), np.float32)
    out[0, :4, 0] = [320, 320, 64, 64]          # kotak di tengah input 640
    out[0, 4 + 2, 0] = 0.9                       # kelas 2
    out[0, 4, 1] = 0.0005                        # di bawah conf_min -> dibuang
    k = inferensi.pasca_proses(out, 0.5, (0, 80), (960, 1280), 0.001, 0.7, 300)
    assert len(k) == 1 and k[0].kelas == 2 and k[0].keyakinan == pytest.approx(0.9)
    # x: (288 - 0) / 0,5 = 576 ; y: (288 - 80) / 0,5 = 416
    assert (k[0].x1, k[0].y1, k[0].x2, k[0].y2) == pytest.approx((576, 416, 704, 544))


# ---------- model ONNX
def test_model_sesuai_sha256(cfg):
    assert hashlib.sha256(cfg.model_path.read_bytes()).hexdigest() == cfg.model_sha256


def test_inferensi_gambar_sintetis(detektor):
    k = detektor.prediksi(np.full((480, 640, 3), 120, np.uint8))
    assert isinstance(k, list)
    for b in k:
        assert 0 <= b.x1 <= b.x2 <= 640 and 0 <= b.y1 <= b.y2 <= 480 and 0 < b.keyakinan <= 1 and b.kelas in (0, 1, 2)


@butuh_data
def test_inferensi_setara_hasil_tersimpan(detektor, cfg):
    """Kelas teratas dan keyakinan sama dengan evaluasi tersimpan Ultralytics (selisih < 0,01) pada 20 foto val."""
    acuan = list(csv.DictReader(open(PROYEK / "reports/final_eval_v7/aplikasi/onnx_vs_pt_50_val.csv", encoding="utf-8")))[:20]
    for r in acuan:
        im = gambar.baca_foto((VAL / r["gambar"]).read_bytes(), cfg.ukuran_maks_mb)
        k = detektor.prediksi(gambar.ke_array(im))
        top = max(k, key=lambda b: b.keyakinan) if k else None
        kelas, conf = (top.kelas, top.keyakinan) if top else (-1, 0.0)      # acuan -1 = tanpa kotak
        assert kelas == int(r["kelas_onnx"]), r["gambar"]
        assert abs(conf - float(r["conf_onnx"])) < 0.01, r["gambar"]


def test_foto_besar_diperkecil_dan_orientasi_tetap():
    im = gambar.baca_foto(jpeg(4000, 3000), 10, 2048)
    assert max(im.size) == 2048 and im.size == (2048, 1536)
    im = gambar.baca_foto(jpeg(4000, 3000, exif_orientasi=6), 10, 2048)   # potret setelah koreksi EXIF
    assert im.size == (1536, 2048)
    assert gambar.baca_foto(jpeg(1024, 1024), 10, 2048).size == (1024, 1024)  # foto kecil tidak diubah


def test_saran_tindakan_sekarang_lebih_dulu(aturan):
    from rbs import mesin
    from ui import komponen as ui
    h = mesin.jalankan(mesin.fakta_dari_diagnosis("leaf_blast", "terdeteksi", 0.7), aturan)
    out = ui.daftar_saran(h.saran, mesin.muat_meta())
    assert out.index("Tindakan sekarang") < out.index("Pencegahan musim berikutnya")
    assert out.index("Bakar jerami") < out.index("Pemupukan berimbang")
    assert "Gunakan pestisida sesuai dosis pada label dan anjuran penyuluh setempat." in out
    assert "Teknik Mengendalikan Hama dan Penyakit Padi" in out


def test_pita_tanpa_angka_batas():
    from ui import komponen as ui
    s = ui.pita_keyakinan(0.66, "terdeteksi")
    assert "66%" in s and "29%" not in s and "35%" not in s


def test_potongan_diperbesar():
    from core import visual
    im = Image.new("RGB", (1024, 1024), (60, 120, 60))
    jpg, f = visual.potongan_diperbesar(im, inferensi.Kotak(500, 500, 520, 512, 0.8, 1), "terdeteksi")
    assert Image.open(io.BytesIO(jpg)).size == (480, 480) and f == pytest.approx(3.0)
    _, f2 = visual.potongan_diperbesar(im, inferensi.Kotak(100, 100, 900, 600, 0.8, 2), "terdeteksi")
    assert f2 < 1.0                                        # kotak besar: potongan memuat seluruh kotak, tidak diperbesar


def test_css_tanpa_has_dan_skrip_label():
    from ui import komponen as ui
    assert ":has(" not in ui.css()                         # tampilan tidak bergantung pada CSS :has()
    s = ui.skrip_label()
    assert '"Take Photo": "Ambil foto"' in s and "Unggah foto lain" in s and "MutationObserver" in s


def test_kepala_hasil_menandai_ilustrasi_bila_ada_potongan():
    from ui import komponen as ui
    assert "ada-potongan" in ui.kepala_hasil("leaf_blast", "terdeteksi", ada_potongan=True)
    assert "ada-potongan" not in ui.kepala_hasil("leaf_blast", "terdeteksi", ada_potongan=False)
