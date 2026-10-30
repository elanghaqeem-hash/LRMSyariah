# AGENTS.md — LRMSyariah

## Mandat

Gunakan **`elanghaqeem-hash/LRMSyariah`** sebagai repository tunggal untuk kode dan dokumen teknis proyek Liquidity Risk Management (LRM) Syariah.

Instruksi ini berlaku untuk coding agent yang benar-benar memiliki akses tulis ke GitHub. **ChatGPT tidak otomatis mengirim seluruh isi percakapan ke GitHub**; file harus dibuat/diubah dan commit berhasil dibuat secara eksplisit oleh agent/tool yang tersedia.

## Aturan kerja wajib

1. **Read before write**: verifikasi identitas repository, branch, commit terbaru, struktur, dan isi file sebelum mengedit. Jangan mengasumsikan file yang pernah dibahas dalam chat sudah berada di GitHub.
2. **GitHub-first**: untuk setiap pekerjaan implementasi, perubahan final harus berupa file di repository ini. Jika akses tulis gagal, beritahu pengguna secara eksplisit dan berikan patch yang bisa diterapkan; jangan mengaku sudah push.
3. **Isolasi**: jangan menggunakan repository proyek lain. Jangan menimpa atau menghapus perubahan pihak lain tanpa pemeriksaan diff.
4. **Scope & quality**: implementasikan sesuai kebutuhan yang diberikan, lengkapi tes, error handling, audit trail, dan dokumentasi untuk fitur yang relevan.
5. **Regulatory integrity**: regulasi OJK/BI dan parameter likuiditas (termasuk LCR, NSFR, ILAAP, stress testing) harus dilacak ke rujukan resmi; nilai belum terverifikasi ditandai `[VERIFY]`. Jangan mengklaim regulatory compliance atau production-ready tanpa evidensi.
6. **Security & privacy**: repo ini public. Jangan commit password, token, private key, `.env`, data nasabah, rekening, transaksi bank nyata, atau dokumen confidential; gunakan sample sintetis.
7. **Change traceability**: catat perubahan di `CHANGELOG.md`. Keputusan material/penyimpangan baseline dicatat di `docs/decision-log.md`.
8. **Versioning**: buat commit deskriptif per perubahan. Untuk perubahan kritis (perhitungan risiko, otorisasi, DB, migrations, regulatory model), gunakan feature branch dan pull request dengan pemeriksaan sebelum merge.
9. **Verification**: laporkan perintah/tes yang benar-benar dijalankan, lulus/gagal, serta tautan commit atau PR. Jangan menyamakan commit dengan deploy.
10. **Deployment**: tidak ada deploy otomatis tersirat dari chat. Jalankan deployment hanya setelah target environment tersedia, otorisasi jelas, release gate lulus, dan hasil diverifikasi.

## Format laporan hasil agent

- Ringkasan perubahan dan daftar file yang disentuh
- Hasil pengujian (beserta keterbatasannya)
- Commit SHA/PR URL atau kendala yang mencegah commit
- Dampak pada database, regulasi, keamanan, dan deployment
- Langkah lanjutan yang belum diselesaikan
