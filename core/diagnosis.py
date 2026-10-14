"""Aturan diagnosis per foto (sama dengan evaluasi skripsi dan keputusan tiga tingkat 2026-10-13):

- diagnosis = kelas kotak dengan keyakinan tertinggi;
- terdeteksi       : keyakinan >= ambang_terdeteksi (0,35);
- kemungkinan      : ambang_rendah (0,29) <= keyakinan < ambang_terdeteksi;
- tidak terdeteksi : keyakinan < ambang_rendah, atau tidak ada kotak.
"""
from dataclasses import dataclass, field

TERDETEKSI, KEMUNGKINAN, TIDAK_TERDETEKSI = "terdeteksi", "kemungkinan", "tidak_terdeteksi"


@dataclass(frozen=True)
class HasilDiagnosis:
    penyakit: str | None            # kode kelas (leaf_blast, brown_spot, bacterial_leaf_blight) atau None
    tingkat: str
    keyakinan: float                # keyakinan kotak teratas (0 bila tanpa kotak)
    kotak: tuple = field(default_factory=tuple)   # semua kotak hasil NMS (untuk digambar sesuai aturan tampilan)


def tentukan_tingkat(keyakinan: float, ambang_terdeteksi: float, ambang_rendah: float) -> str:
    if keyakinan >= ambang_terdeteksi:
        return TERDETEKSI
    if keyakinan >= ambang_rendah:
        return KEMUNGKINAN
    return TIDAK_TERDETEKSI


def diagnosis(kotak, kelas, ambang_terdeteksi: float, ambang_rendah: float) -> HasilDiagnosis:
    if not kotak:
        return HasilDiagnosis(None, TIDAK_TERDETEKSI, 0.0, ())
    top = max(kotak, key=lambda b: b.keyakinan)
    return HasilDiagnosis(kelas[top.kelas], tentukan_tingkat(top.keyakinan, ambang_terdeteksi, ambang_rendah), top.keyakinan, tuple(kotak))


def kotak_untuk_digambar(hasil: HasilDiagnosis, kelas, ambang_rendah: float):
    """Kotak berkelas sama dengan diagnosis dan berkeyakinan >= ambang_rendah. Tidak ada kotak bila tidak terdeteksi."""
    if hasil.tingkat == TIDAK_TERDETEKSI or hasil.penyakit is None:
        return []
    return [b for b in hasil.kotak if kelas[b.kelas] == hasil.penyakit and b.keyakinan >= ambang_rendah]
