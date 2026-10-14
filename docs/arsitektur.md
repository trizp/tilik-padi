# Arsitektur

Tampilan (Streamlit) dipisahkan dari logika. `core/` dan `rbs/` tidak mengimpor Streamlit, sehingga bisa diuji dan dipakai ulang tanpa
antarmuka. `ui/komponen.py` hanya membuat string HTML.

```mermaid
flowchart TD
    U[Pengguna: kamera HP atau unggah JPG/PNG maks. 10 MB] --> S[streamlit_app.py<br/>tampilan saja]
    S -->|bytes foto| A[core/alur.py<br/>periksa_foto]
    A --> G[core/gambar.py<br/>periksa berkas, exif_transpose,<br/>RGB, perkecil > 2048 px]
    G --> I[core/inferensi.py<br/>letterbox 640, ONNX Runtime CPU,<br/>NMS per kelas, skala balik]
    M[(models/v7_deploy_yolo11s_s2.onnx)] --> I
    C[(config.yaml<br/>ambang 0,35 dan 0,29, teks)] --> A
    I --> D[core/diagnosis.py<br/>kotak teratas, tiga tingkat]
    D --> R[rbs/mesin.py<br/>forward chaining]
    RY[(rbs/rules.yaml)] --> R
    D --> V[core/visual.py<br/>kotak tebal berwarna tingkat,<br/>potongan diperbesar, JPEG]
    R --> S
    V --> S
    S --> K[ui/komponen.py + ui/ilustrasi.py<br/>kepala hasil, ilustrasi SVG, pita keyakinan,<br/>saran berkelompok, jejak, peringatan]
```

## Alur forward chaining

```mermaid
flowchart TD
    F0["Fakta awal:<br/>penyakit, tingkat, keyakinan"] --> L{"Ada aturan yang belum aktif<br/>dan semua syaratnya benar?"}
    L -- tidak --> E["Berhenti.<br/>Tampilkan saran dan jejak"]
    L -- ya --> P["Aktifkan aturan pertama (urutan rules.yaml):<br/>tambah fakta baru, tambah saran, catat jejak"]
    P --> L
```

Rantai yang terjadi (dua putaran, lalu berhenti):

| Tingkat | Putaran 1 | Fakta baru | Putaran 2 | Saran |
|---|---|---|---|---|
| terdeteksi | D01 Diagnosis diterima | `diagnosis = <penyakit>` | R001 / R002 / R003 | butir Tabel 3.1: tindakan sekarang [S] + pencegahan musim berikutnya [P] |
| kemungkinan | K01 Diagnosis belum pasti | `dugaan`, `perlu_konfirmasi = ya` | K02 | konfirmasi ke penyuluh + pencegahan umum |
| tidak terdeteksi | N01 Tidak ada penyakit yang dikenali | `perlu_foto_ulang = ya` | N02 | foto ulang + tanya penyuluh + pencegahan umum |

## Memori dan kecepatan

Diukur di folder proyek skripsi dengan Chrome headless (hasil: `docs/uji/sumber_daya.md`):
- RAM diam 145 MB, puncak 250 MB, dan 158 MB setelah 11 foto;
- waktu inti ±0,1 detik per foto di CPU laptop.

Penghemat memori:
- model dimuat sekali (`st.cache_resource`);
- arena memori ONNX Runtime dimatikan;
- foto > 2048 px didekode kecil;
- foto hasil dikirim sebagai JPEG.
