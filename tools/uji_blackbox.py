#!/usr/bin/env python3
"""
uji_blackbox.py - Uji black-box lewat jalur yang sama dengan tampilan (core.alur.periksa_foto).
10 foto VAL prov_v7 dipilih ACAK per kelas (seed 20261014), bukan dipilih berdasarkan hasil: 3 Blast, 3 Brown spot, 2 BLB,
2 daun sehat (ds4). Ditambah 4 skenario masukan (turunan foto pertama, dibuat di memori): PNG, EXIF diputar, bukan gambar, >10 MB.
Catatan: model aplikasi dilatih dengan train+val+test prov_v7, jadi foto VAL termasuk data latihnya. Uji ini memeriksa perilaku
sistem, bukan ketepatan pada foto baru.

  app/.venv/Scripts/python.exe app/tools/uji_blackbox.py
Keluaran: app/docs/uji/blackbox.md dan blackbox.json
"""
import csv
import io
import json
import random
import sys
from pathlib import Path

from PIL import Image

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
from core import alur, gambar, inferensi, konfigurasi  # noqa: E402
from rbs import mesin  # noqa: E402
from ui.komponen import LABEL_TINGKAT, PENYAKIT  # noqa: E402

PROYEK = APP.parent
VAL = PROYEK / "data/processed/prov_v7/images/val"
SEED = 20261014
JUMLAH = {"leaf_blast": 3, "brown_spot": 3, "bacterial_leaf_blight": 2, "background": 2}
ATURAN_KHUSUS = {"leaf_blast": "R001", "brown_spot": "R003", "bacterial_leaf_blight": "R002"}


def nama(p):
    return PENYAKIT[p]["nama"] if p in PENYAKIT else "tidak ada"


def pilih_foto():
    man = [r for r in csv.DictReader(open(PROYEK / "data/processed/prov_v7/manifest.csv", encoding="utf-8")) if r["split"] == "val"]
    rng = random.Random(SEED)
    out = []
    for kelas, n in JUMLAH.items():
        calon = sorted(r["file"] for r in man if r["class"] == kelas and (kelas != "background" or r["source"] == "ds4"))
        out += [(kelas, f) for f in rng.sample(calon, n)]
    return out


def ringkas(h):
    d = h.diagnosis
    return {"diagnosis": d.penyakit or "tidak_ada", "tingkat": d.tingkat, "keyakinan": round(d.keyakinan, 4),
            "aturan": "+".join(L.aturan.id for L in h.inferensi.jejak), "kotak_digambar": h.kotak_digambar}


def main():
    cfg = konfigurasi.muat()
    det = inferensi.Detektor(cfg.model_path, cfg.imgsz, cfg.conf_min, cfg.iou, cfg.max_det)
    aturan = mesin.muat_aturan()
    baris = []
    foto = pilih_foto()
    for no, (kelas, f) in enumerate(foto, 1):
        h = ringkas(alur.periksa_foto((VAL / f).read_bytes(), cfg, det, aturan))
        if kelas == "background":
            harap = "Tidak terdeteksi; saran foto ulang dan pencegahan umum (N01, N02)"
            sesuai = h["tingkat"] == "tidak_terdeteksi" and h["aturan"] == "N01+N02"
        else:
            harap = f"{nama(kelas)}, terdeteksi; saran {ATURAN_KHUSUS[kelas]} (D01, {ATURAN_KHUSUS[kelas]})"
            sesuai = h["diagnosis"] == kelas and h["tingkat"] == "terdeteksi" and h["aturan"] == f"D01+{ATURAN_KHUSUS[kelas]}"
        if h["tingkat"] == "tidak_terdeteksi":
            aktual = f"Tidak terdeteksi (keyakinan tertinggi {100 * h['keyakinan']:.1f}%); aturan {h['aturan'].replace('+', ', ')}".replace(".", ",", 1)
        else:
            aktual = f"{nama(h['diagnosis'])}, {LABEL_TINGKAT[h['tingkat']].lower()} ({100 * h['keyakinan']:.0f}%); aturan {h['aturan'].replace('+', ', ')}"
        baris.append({"no": no, "masukan": f"VAL {f} (label: {nama(kelas) if kelas != 'background' else 'daun sehat'})",
                      "harapan": harap, "aktual": aktual, "sesuai": sesuai, **h})

    # skenario masukan khusus (turunan foto pertama, di memori)
    asal_f = foto[0][1]
    asal = (VAL / asal_f).read_bytes()
    ref = ringkas(alur.periksa_foto(asal, cfg, det, aturan))
    im = Image.open(io.BytesIO(asal)).convert("RGB")
    png = io.BytesIO()
    im.save(png, "PNG")
    rot = io.BytesIO()
    ex = Image.Exif()
    ex[0x0112] = 6                                   # penampil harus memutar 90 derajat searah jarum jam
    im.transpose(Image.Transpose.ROTATE_90).save(rot, "JPEG", quality=95, exif=ex.tobytes())
    khusus = [("Foto no. 1 disimpan ulang sebagai PNG", png.getvalue(), "Hasil sama dengan foto no. 1 (kelas dan tingkat)"),
              ("Foto no. 1 diputar 90 derajat dengan tag EXIF orientasi 6", rot.getvalue(),
               "Orientasi dikoreksi; kelas dan tingkat sama dengan foto no. 1"),
              ("Berkas teks berakhiran .jpg", b"bukan foto", "Ditolak dengan pesan cara memperbaiki"),
              ("Berkas 10,5 MB", b"\xff\xd8" + b"\x00" * int(10.5 * 1024 * 1024), "Ditolak karena melebihi 10 MB")]
    for i, (masuk, data, harap) in enumerate(khusus, len(baris) + 1):
        try:
            h = ringkas(alur.periksa_foto(data, cfg, det, aturan))
            aktual = f"{nama(h['diagnosis'])}, {LABEL_TINGKAT[h['tingkat']].lower()} ({100 * h['keyakinan']:.0f}%)"
            sesuai = (h["diagnosis"], h["tingkat"]) == (ref["diagnosis"], ref["tingkat"]) and "Ditolak" not in harap
        except gambar.FotoDitolak as e:
            h, aktual = {}, f"Ditolak: \"{e}\""
            sesuai = "Ditolak" in harap
        baris.append({"no": i, "masukan": masuk, "harapan": harap, "aktual": aktual, "sesuai": sesuai, **h})

    n_foto = sum(1 for b in baris[:10] if b["sesuai"])
    n_khusus = sum(1 for b in baris[10:] if b["sesuai"])
    (APP / "docs/uji/blackbox.json").write_text(json.dumps({"seed": SEED, "foto_sesuai": n_foto, "khusus_sesuai": n_khusus, "baris": baris},
                                                           indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# Uji black-box", "",
          f"Jalur: `core.alur.periksa_foto` (sama dengan tampilan). 10 foto VAL prov_v7 dipilih acak per kelas (seed {SEED}),",
          "bukan berdasarkan hasil. Model aplikasi dilatih dengan train+val+test, jadi foto VAL termasuk data latihnya: uji ini memeriksa",
          "perilaku sistem, bukan ketepatan pada foto baru.", "",
          f"**Foto VAL: {n_foto}/10 sesuai harapan. Skenario masukan khusus: {n_khusus}/4 sesuai.**", "",
          "| No | Masukan | Hasil diharapkan | Hasil aktual | Sesuai |", "|---|---|---|---|---|"]
    md += [f"| {b['no']} | {b['masukan']} | {b['harapan']} | {b['aktual']} | {'ya' if b['sesuai'] else 'TIDAK'} |" for b in baris]
    (APP / "docs/uji/blackbox.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return baris


if __name__ == "__main__":
    main()
