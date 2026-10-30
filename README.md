# LRMSyariah — Liquidity Risk Management System

Repository pusat pengembangan **Liquidity Risk Management (LRM) Syariah** untuk kebutuhan manajemen risiko likuiditas bank syariah.

> **Status:** repository awal (scaffold dokumentasi). Modul aplikasi, perhitungan, koneksi database, dan deployment belum diimplementasikan di repository ini.

## Sumber kebenaran (source of truth)

- **Kode aplikasi, konfigurasi non-rahasia, dan dokumentasi teknis:** repository GitHub ini.
- **Branch utama:** `main`.
- **Instruksi coding agent:** [AGENTS.md](./AGENTS.md).
- **Riwayat perubahan:** [CHANGELOG.md](./CHANGELOG.md).
- **Keputusan arsitektur/metodologi:** [docs/decision-log.md](./docs/decision-log.md).

Materi dan keputusan dari percakapan ChatGPT **belum menjadi perubahan repository** hingga ditulis sebagai file dan berhasil di-commit melalui GitHub. Percakapan tidak tersinkron otomatis sebagai kode.

## Alur perubahan melalui ChatGPT

1. Baca kondisi terbaru repository, cabang aktif, file terkait, dan instruksi `AGENTS.md`.
2. Terapkan perubahan pada file yang relevan di repository ini, tanpa menyisipkan rahasia atau data bank.
3. Uji dan validasi sesuai cakupan perubahan; laporkan pemeriksaan yang belum dapat dijalankan.
4. Update `CHANGELOG.md` dan, bila ada keputusan penting, `docs/decision-log.md`.
5. Commit/push ke GitHub melalui konektor yang tersedia; gunakan pull request untuk perubahan berisiko tinggi.
6. Sampaikan tautan commit/pull request dan status perubahan kepada pengguna. **Jangan menyatakan sudah tersimpan bila belum terkonfirmasi GitHub.**

## Tata kelola dan keamanan

- Repo **public**: jangan unggah kredensial, API key, access token, `.env`, data nasabah, data bank yang bersifat rahasia, hasil uji produksi, maupun dokumen berizin terbatas.
- Parameter regulasi dan metodologi perbankan yang belum tervalidasi wajib ditandai `[VERIFY]` dan diverifikasi dengan dokumen resmi sebelum produksi.
- Tidak ada auto-deploy ke produksi tanpa pengujian, persetujuan, dan verifikasi release gate.
- Setelah aplikasi dikembangkan, otomatisasi CI/CD dapat ditambahkan secara terpisah. GitHub Actions tidak bisa mendeteksi teks percakapan ChatGPT yang belum di-commit.

## Langkah pengembangan berikutnya

Masukkan spesifikasi/prompt pengembangan LRM Syariah yang telah disetujui ke direktori `docs/`, kemudian lanjutkan per work package secara terkontrol.
