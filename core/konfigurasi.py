"""Memuat app/config.yaml. Jalur relatif di config dihitung dari folder app/."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

APP_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Konfigurasi:
    model_path: Path
    model_sha256: str
    imgsz: int
    iou: float
    conf_min: float
    max_det: int
    ambang_terdeteksi: float
    ambang_rendah: float
    ukuran_maks_mb: float
    sisi_maks_proses: int
    jenis_berkas: tuple
    kelas: tuple
    teks: dict = field(default_factory=dict)
    sumber_data: tuple = ()


def muat(path=None) -> Konfigurasi:
    path = Path(path) if path else APP_DIR / "config.yaml"
    c = yaml.safe_load(path.read_text(encoding="utf-8"))
    m, a, u = c["model"], c["ambang"], c["unggahan"]
    if not (0 < a["rendah"] < a["terdeteksi"] < 1):
        raise ValueError("config.yaml: syarat 0 < ambang.rendah < ambang.terdeteksi < 1 tidak terpenuhi")
    return Konfigurasi(
        model_path=(APP_DIR / m["path"]).resolve(),
        model_sha256=m.get("sha256", ""),
        imgsz=int(m["imgsz"]),
        iou=float(m["iou"]),
        conf_min=float(m["conf_min"]),
        max_det=int(m["max_det"]),
        ambang_terdeteksi=float(a["terdeteksi"]),
        ambang_rendah=float(a["rendah"]),
        ukuran_maks_mb=float(u["ukuran_maks_mb"]),
        sisi_maks_proses=int(u.get("sisi_maks_proses", 2048)),
        jenis_berkas=tuple(u["jenis"]),
        kelas=tuple(m["kelas"]),
        teks=c.get("teks", {}),
        sumber_data=tuple(c.get("sumber_data", [])),
    )
