# Latihan (arsip)

Folder ini berisi kode latihan yang dibuat sebelum package `nasdaq_mme_idx`
dan script test asli (`test_fix_send_order_time_duration.py`,
`test_fix_send_multi_orders.py`) diterima dari mentor.

Isinya (`messages.py`, `test_fix_send_order_limit.py`, dst) adalah hasil
rekonstruksi mandiri berdasarkan dokumen spek FIX resmi IDX
(`NDAQ_Trading_FIX_OE_ProtSpec_IDX.pdf`), dipakai untuk belajar cara kerja
library `nasdaq_protocols.fix` (Field, DataSegment, Group, GroupContainer,
Message, FixSession) sebelum bahan asli tersedia.

**Sudah tidak dipakai untuk pengujian sungguhan** — digantikan oleh script
asli di `tests/idx_mme_test_script/fix/` yang memakai `nasdaq_mme_idx`.
Disimpan di sini (bukan dihapus) sebagai referensi belajar.
