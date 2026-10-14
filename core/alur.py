"""Alur lengkap satu foto: baca -> deteksi -> diagnosis tiga tingkat -> forward chaining -> foto bertanda kotak.
Dipakai oleh tampilan Streamlit dan oleh uji black-box (jalur yang sama persis)."""
from dataclasses import dataclass

from core import diagnosis as dg
from core import gambar, visual
from rbs import mesin


@dataclass
class HasilPemeriksaan:
    foto_bertanda: bytes            # JPEG siap tampil (lebih kecil daripada PNG bawaan st.image)
    diagnosis: dg.HasilDiagnosis
    inferensi: mesin.HasilInferensi
    fakta_awal: dict
    kotak_digambar: int
    potongan: bytes | None = None   # JPEG potongan diperbesar dari kotak berkeyakinan tertinggi (None bila tidak terdeteksi)
    perbesaran: float = 0.0


def periksa_foto(data: bytes, cfg, detektor, aturan) -> HasilPemeriksaan:
    """Melempar gambar.FotoDitolak bila berkas bukan foto yang valid. Foto tidak ditulis ke disk."""
    im = gambar.baca_foto(data, cfg.ukuran_maks_mb, cfg.sisi_maks_proses)
    kotak = detektor.prediksi(gambar.ke_array(im))
    hasil = dg.diagnosis(kotak, cfg.kelas, cfg.ambang_terdeteksi, cfg.ambang_rendah)
    gambar_kotak = dg.kotak_untuk_digambar(hasil, cfg.kelas, cfg.ambang_rendah)
    tampil = visual.ke_jpeg(visual.gambar_kotak(im, gambar_kotak, hasil.tingkat))
    fakta = mesin.fakta_dari_diagnosis(hasil.penyakit, hasil.tingkat, hasil.keyakinan)
    inf = mesin.jalankan(fakta, aturan)
    potongan, perbesaran = None, 0.0
    if gambar_kotak:
        teratas = max(gambar_kotak, key=lambda b: b.keyakinan)
        potongan, perbesaran = visual.potongan_diperbesar(im, teratas, hasil.tingkat)
    del im
    return HasilPemeriksaan(tampil, hasil, inf, fakta, len(gambar_kotak), potongan, perbesaran)
