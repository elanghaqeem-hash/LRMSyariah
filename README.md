# LRMSyariah — Liquidity Risk Management System

Repository pusat pengembangan **Liquidity Risk Management (LRM) Syariah** untuk kebutuhan manajemen risiko likuiditas bank syariah.

> **Status (31 Oktober 2026):** fondasi WP0–WP2 sudah diimpor dan diuji lokal. WP3–WP13, perhitungan LCR/NSFR, validasi model, PostgreSQL aktual, SSO, UAT dan produksi **belum** selesai.

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

## Kode fondasi yang diimpor

- Source: [`src/`](./src/) — pure engine foundation, data contracts, regulatory governance.
- Pengujian: [`tests/`](./tests/) — 113 pengujian lokal lulus pada baseline WP0–WP2; belum mewakili kesiapan produksi.
- Data sintetis: [`examples/synthetic/`](./examples/synthetic/) — tidak mengandung data nasabah nyata.
- Migrasi: [`migrations/`](./migrations/) — SQL/Alembic disiapkan; **belum** diuji pada PostgreSQL Bank.
- Ringkasan paket asal: [`docs/engineering/WP0-WP2-README.md`](./docs/engineering/WP0-WP2-README.md).
- Temuan dan batas penerimaan: [`docs/audit/README.md`](./docs/audit/README.md) dan [`docs/audit/BASELINE-OPEN-GAPS.md`](./docs/audit/BASELINE-OPEN-GAPS.md).

**Penting:** seluruh parameter dan pemetaan akad Bank masih belum aktif/disetujui. Jangan digunakan untuk perhitungan atau pelaporan resmi. CI GitHub dan release gate harus diverifikasi terpisah.

## Langkah pengembangan berikutnya

Masukkan spesifikasi/prompt pengembangan LRM Syariah yang telah disetujui ke direktori `docs/`, kemudian lanjutkan per work package secara terkontrol.
