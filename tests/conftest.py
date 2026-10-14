import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
PROYEK = APP.parent
VAL = PROYEK / "data/processed/prov_v7/images/val"

butuh_data = pytest.mark.skipif(not VAL.exists(), reason="foto VAL proyek tidak tersedia (repositori aplikasi tidak memuat dataset)")


@pytest.fixture(scope="session")
def cfg():
    from core import konfigurasi
    return konfigurasi.muat()


@pytest.fixture(scope="session")
def aturan():
    from rbs import mesin
    return mesin.muat_aturan()


@pytest.fixture(scope="session")
def detektor(cfg):
    from core import inferensi
    return inferensi.Detektor(cfg.model_path, cfg.imgsz, cfg.conf_min, cfg.iou, cfg.max_det)
