# Decision Log — LRMSyariah

## ADR-0001 — GitHub sebagai single source of truth

**Tanggal:** 2026-10-30  
**Status:** Accepted  
**Repository:** https://github.com/elanghaqeem-hash/LRMSyariah  
**Branch utama:** `main`

### Latar belakang

Pengembangan LRM Syariah dilakukan secara bertahap, termasuk bantuan melalui ChatGPT/coding agent. File yang hanya dibahas di chat tidak otomatis tersimpan di repository, sehingga diperlukan pusat versi kode yang dapat diaudit.

### Keputusan

- Seluruh kode, konfigurasi non-rahasia, dan dokumen engineering yang telah disetujui disimpan di repository ini dengan commit yang dapat ditelusuri.
- Setiap penyelesaian perubahan harus menyertakan hasil commit/PR dan pengujian yang dapat dibuktikan.
- Perubahan kritis melalui branch dan PR agar tidak langsung memengaruhi `main` tanpa review.
- Diskusi di ChatGPT adalah sumber instruksi kerja, **bukan event sinkronisasi otomatis**. Push dilakukan ketika tool/agent menulis commit dengan akses yang sah.
- Deployment adalah langkah terpisah dengan release gate dan evidensi verifikasi.
- Karena repository public, hanya artefak yang tidak sensitif boleh disimpan.

### Dampak

Tidak ada implementasi aplikasi atau integrasi sinkronisasi percakapan yang diklaim telah dibuat oleh keputusan ini. Implementasi CI/CD dan pengaturan privasi dapat dilakukan pada tahap berikutnya.
