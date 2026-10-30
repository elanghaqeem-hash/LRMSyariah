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


## ADR-0002 — Import baseline WP0–WP2 via PR terisolasi

**Tanggal:** 2026-10-31  
**Status:** Accepted for engineering baseline; NOT approved for production

- Mempertahankan seluruh scaffold repository, AGENTS.md, dan kebijakan GitHub-first.
- Import source code, dokumentasi publik nonrahasia, pengujian dan data sintetis melalui branch `feat/import-wp0-wp2-audit-baseline-20261031` dan review PR.
- Tidak memasukkan proposal Bank PDF, data nasabah nyata, maupun audit laporan yang mungkin mengandung rincian kontraktual ke repository public.
- WP2 belum diverifikasi terhadap PostgreSQL aktual; parameter regulatori dan mapping akad tidak boleh dipakai sebelum approval Bank.
- `main` belum menunjukkan kesiapan produksi; perpindahan dari WP2 ke WP3 memerlukan audit integritas dan konfirmasi release gate.


## ADR-0003 — WP3 immutable CalculationRun, audit ledger (2026-10-31)
**Status:** Engineering implemented; production HOLD.
- Freeze source/parameter snapshots at creation and APPROVED results permanently.
- Corrections create a new run pointing to the approved predecessor.
- AuditEvent append-only, canonical SHA-256 chain; restricted PostgreSQL role and externally anchored hash required before production.
- Only approved runs may be reproduced on exact semver+git SHA engine.
- Synthetic SQLite test doubles are not evidence of production PostgreSQL security.
