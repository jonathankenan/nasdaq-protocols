# idx_mme_test_script

Folder ini menampung test script pytest untuk pengujian MBP di sistem
MME IDX (test run MME-OUCH-FIX-SQF), sesuai dokumen
"Konfigurasi dan Mapping File Pytest".

Semua script di sini bergantung pada package internal `nasdaq_mme_idx`
(belum publik, harus diminta ke mentor/tim OpenWay-IDX) — package ini
menyediakan definisi pesan FIX yang sudah sesuai spesifikasi IDX
(dibangun di atas class `Header`, `Trailer`, `DataSegment`, `Message`
dari modul `nasdaq_protocols.fix`).

## Prasyarat sebelum script di sini bisa jalan

1. Dapatkan file `nasdaq_mme_idx-0.2.0rc2.dev18+g76893a8.tar.gz` dari mentor.
2. Install ke venv project: `pip install nasdaq_mme_idx-0.2.0rc2.dev18+g76893a8.tar.gz`
3. Dapatkan isi asli file `.py` test script di bawah ini dari mentor/tim
   (isinya proprietary, tidak bisa direkonstruksi tanpa spesifikasi field
   FIX milik IDX) — cukup copy ke folder yang sesuai (fix/ atau ouch/ atau
   mme_max_conn/).
4. Sesuaikan isi file CSV data & credential di masing-masing folder (lihat
   contoh header yang sudah disiapkan di tiap CSV).

## Konfigurasi environment (dev3)

- FIX  : 172.18.2.132 | 8200
- OUCH : 172.18.2.132 | 8600
- ITCH : 172.18.2.132 | 21600
- User dev3: BKJFE7 / BKJFE8 / BKJFE9 (password: tanyakan ke mentor)

## Konfigurasi environment (AT1 PreProd)

- FIX : 172.18.2.141 | 8201
- User (gantian, request saja): ROJFE1 | P@ssw0rd1

## Daftar file yang perlu diminta/disalin dari mentor

### fix/ — Single Order
- test_fix_send_order_limit.py — create order RG/TN
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_send_order_limit.py`
- test_fix_amend_message.py — amend order
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_amend_message.py`
- test_fix_withdraw_message.py — withdraw order
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_withdraw_message.py`
- test_fix_one_side.py — order nego 1 sisi
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_one_side.py -s`
- test_fix_two_side.py — order nego 2 sisi
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_two_side.py -s`
- test_fix_mass_quote.py — mass quote (biasa dipakai bareng tim LDT)
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_mass_quote.py`
- test_fix_multilevel_mass_quote.py — multilevel mass quote (biasa dipakai bareng tim LDT)
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_multilevel_mass_quote.py`

### fix/ — Multi Order
- test_fix_send_order_time_duration.py — send order selama waktu tertentu (biasa untuk test MBP)
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_send_order_time_duration.py`
  data: data_order_time_window.csv, credential_time_window.csv
- test_fix_send_multi_orders.py — send order sebanyak angka yang ditentukan
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_send_multi_orders.py`
  data: data_orders.csv, pytest_credentials_fix.csv
- test_fix_send_order_time_range.py — send order dengan start & end time
  `python -m pytest tests/idx_mme_test_script/fix/test_fix_send_order_time_range.py`

### ouch/ — Single Order
- test_ouch_send_message.py — create order RG/TN
- test_ouch_amend_message.py — amend order
- test_ouch_wd_message.py — withdraw order

### ouch/ — Multi Order
- test_ouch_send_mass_order.py — send order sebanyak angka yang ditentukan

### mme_max_conn/
- test_multi_login_FIX.py — pengujian maksimum koneksi user protokol FIX
- test_multi_login_ITCH.py — pengujian maksimum koneksi user protokol ITCH
- test_multi_login_OUCH.py — pengujian maksimum koneksi user protokol OUCH

## Cara menjalankan (setelah semua siap)

```
env\Scripts\activate.bat
env\Scripts\python.exe -m pytest tests\idx_mme_test_script\fix\test_fix_send_order_time_duration.py
```

Hasil log otomatis tersimpan sebagai `orders_YYYYMMDD_HHMMSS.log`.
