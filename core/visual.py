"""Menggambar kotak bercak pada salinan foto yang diperkecil untuk tampilan."""
import io

from PIL import Image, ImageDraw

WARNA_TINGKAT = {"terdeteksi": "#A4442A", "kemungkinan": "#C9A227", "tidak_terdeteksi": "#4F6D8A"}


def gambar_kotak(im: Image.Image, kotak, tingkat: str, sisi_maks: int = 1280) -> Image.Image:
    s = min(1.0, sisi_maks / max(im.size))
    tampil = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR) if s < 1 else im.copy()
    d = ImageDraw.Draw(tampil)
    tebal = max(6, round(max(tampil.size) / 90))      # tetap tebal setelah foto diperkecil di layar HP
    warna = WARNA_TINGKAT[tingkat]
    for b in kotak:
        xy = [b.x1 * s, b.y1 * s, b.x2 * s, b.y2 * s]
        luar = max(2, tebal // 3)                      # garis luar Tinta: kotak tetap terlihat di daun terang/kuning
        d.rectangle([xy[0] - luar, xy[1] - luar, xy[2] + luar, xy[3] + luar], outline="#1F2D24", width=tebal + 2 * luar)
        d.rectangle(xy, outline=warna, width=tebal)
    return tampil


def ke_jpeg(im: Image.Image, kualitas: int = 85) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=kualitas)
    return buf.getvalue()


def potongan_diperbesar(im: Image.Image, kotak, tingkat: str, keluaran: int = 480):
    """Potongan persegi di sekitar kotak (keyakinan tertinggi), untuk ditampilkan selebar setengah foto utama.
    Sisi potongan = maks(1,6 x sisi kotak terpanjang, sisi foto terpendek / 6), dibatasi sisi foto terpendek. Dengan tampilan
    setengah lebar foto, perbesaran relatif terhadap foto utama = lebar_foto / (2 x sisi potongan): 3x untuk bercak kecil,
    makin kecil untuk bercak besar. Kembalikan (JPEG bytes, perbesaran)."""
    W, H = im.size
    pendek = min(W, H)
    bw, bh = kotak.x2 - kotak.x1, kotak.y2 - kotak.y1
    sisi = min(max(1.6 * max(bw, bh), pendek / 6), pendek)
    cx, cy = (kotak.x1 + kotak.x2) / 2, (kotak.y1 + kotak.y2) / 2
    x0 = min(max(cx - sisi / 2, 0), W - sisi)
    y0 = min(max(cy - sisi / 2, 0), H - sisi)
    pot = im.crop((round(x0), round(y0), round(x0 + sisi), round(y0 + sisi))).resize((keluaran, keluaran), Image.LANCZOS)
    s = keluaran / sisi
    d = ImageDraw.Draw(pot)
    xy = [(kotak.x1 - x0) * s, (kotak.y1 - y0) * s, (kotak.x2 - x0) * s, (kotak.y2 - y0) * s]
    d.rectangle([xy[0] - 3, xy[1] - 3, xy[2] + 3, xy[3] + 3], outline="#1F2D24", width=9)
    d.rectangle(xy, outline=WARNA_TINGKAT[tingkat], width=5)
    return ke_jpeg(pot), W / (2 * sisi)
