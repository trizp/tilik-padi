"""Uji black-box (10 foto VAL + 4 skenario masukan). Yang dipastikan: sistem memberi keluaran yang konsisten untuk setiap masukan
(aturan aktif sesuai tingkat, masukan buruk ditolak). Ketepatan diagnosis dilaporkan di docs/uji/blackbox.md, tidak di-assert."""
import sys

from conftest import APP, butuh_data

sys.path.insert(0, str(APP / "tools"))

POLA = {"terdeteksi": "D01+R", "kemungkinan": "K01+K02", "tidak_terdeteksi": "N01+N02"}


@butuh_data
def test_blackbox():
    import uji_blackbox
    baris = uji_blackbox.main()
    assert len(baris) == 14
    for b in baris[:10]:
        assert b["aturan"].startswith(POLA[b["tingkat"]]), b
        assert (b["kotak_digambar"] > 0) == (b["tingkat"] != "tidak_terdeteksi"), b
    assert all(b["sesuai"] for b in baris[10:]), [b for b in baris[10:] if not b["sesuai"]]
