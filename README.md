# 🏦 ATM Network Liquidity Optimization Dashboard

Dashboard interaktif berbasis **Streamlit** untuk Divisi *Operations & Treasury* dalam
menganalisis kinerja kas jaringan ATM dan mengidentifikasi peluang efisiensi biaya
berbasis model **Economic Order Quantity (EOQ)** — tanpa mengorbankan tingkat layanan
(risiko stockout).

Dashboard ini adalah versi interaktif dari analisis Excel & presentasi PPTX
sebelumnya, dengan tambahan: filter dinamis, asumsi yang dapat diubah langsung
(what-if analysis), dan visualisasi yang saling terhubung secara real-time.

---

## ✨ Fitur Utama

| Tab | Isi |
|---|---|
| 📊 **Ringkasan Eksekutif** | KPI utama, struktur biaya, tren bulanan, temuan otomatis |
| 💰 **Biaya & Utilisasi** | Komposisi holding vs logistik, utilisasi kas per ATM, distribusi harian |
| 🎯 **Optimasi EOQ** | Kalkulasi kuantitas order optimal, tabel detail per ATM, unduh CSV |
| 📈 **Volatilitas & Musiman** | Koefisien variasi permintaan, pola weekday/weekend, tren bulanan per lokasi |
| 🗺️ **Wilayah & Logistik** | Biaya per wilayah, biaya CIT per trip, treemap wilayah × tipe lokasi |
| 🔁 **Kebijakan Replenishment** | Sebaran trigger isi ulang, siklus replenishment, insiden stockout |
| 📋 **Rekomendasi** | 6 rekomendasi kebijakan yang dihasilkan otomatis dari data & filter aktif |
| 📁 **Data Explorer** | Jelajahi & unduh data mentah maupun hasil kalkulasi |

**Semua angka & narasi otomatis menyesuaikan** dengan filter (tipe lokasi, wilayah,
ATM, rentang tanggal) dan asumsi model (tingkat biaya modal, batas kapasitas EOQ)
yang diatur di sidebar — cocok untuk sesi diskusi/what-if bersama tim Treasury.

---

## 🚀 Cara Menjalankan

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Jalankan aplikasi
```bash
streamlit run app.py
```

Aplikasi akan terbuka otomatis di browser pada `http://localhost:8501`.

---

## 📂 Struktur File

```
atm_liquidity_dashboard/
├── app.py                                   # Aplikasi Streamlit utama
├── atm_liquidity_optimization_dataset.csv    # Dataset contoh (20 ATM x 200 hari)
├── requirements.txt                          # Daftar dependency Python
└── README.md                                 # Dokumen ini
```

---

## 📋 Menggunakan Dataset Sendiri

Dashboard dapat memuat dataset lain melalui tombol **"Unggah dataset CSV"** di
sidebar. File CSV wajib memiliki kolom berikut (nama harus persis sama):

| Kolom | Tipe | Keterangan |
|---|---|---|
| `Log_Date` | tanggal | Tanggal observasi harian |
| `ATM_ID` | teks | ID unik mesin ATM |
| `Location_Type` | teks | Tipe lokasi (mis. Shopping Mall, Office Building, dst) |
| `Region` | teks | Wilayah/region ATM |
| `Max_Capacity_IDR` | angka | Kapasitas maksimum kas ATM |
| `Beginning_Cash_IDR` | angka | Saldo kas awal hari |
| `Replenishment_Amount_IDR` | angka | Nominal isi ulang pada hari tsb (0 jika tidak ada) |
| `Target_Demand_IDR` | angka | Target/estimasi permintaan |
| `Actual_Withdrawal_IDR` | angka | Realisasi penarikan |
| `Ending_Cash_IDR` | angka | Saldo kas akhir hari |
| `Is_Stockout` | 0/1 | Indikator kehabisan kas |
| `Holding_Cost_IDR` | angka | Biaya modal (opportunity cost) dana idle hari tsb |
| `Logistics_Cost_IDR` | angka | Biaya logistik CIT hari tsb |
| `Stockout_Penalty_Cost_IDR` | angka | Biaya penalti stockout hari tsb |

---

## 🧮 Metodologi EOQ

Kuantitas order optimal dihitung dengan rumus klasik *Economic Order Quantity*:

```
Q* = sqrt( 2 x D x S / H )
```

- **D** = rata-rata penarikan harian per ATM
- **S** = rata-rata biaya logistik (CIT) per trip isi ulang
- **H** = tingkat biaya modal harian (opportunity cost dana idle)

Nilai default **H** diturunkan otomatis dari median rasio
`Holding_Cost_IDR ÷ Beginning_Cash_IDR` pada dataset yang dimuat, namun dapat
diubah manual di sidebar untuk analisis sensitivitas (what-if). Kuantitas order
EOQ juga dibatasi agar tidak melebihi kapasitas fisik ATM (dapat diatur di
**Pengaturan Lanjutan**).

---

## 🛠️ Teknologi

- [Streamlit](https://streamlit.io/) — kerangka aplikasi web interaktif
- [Pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/) — pengolahan data
- [Plotly](https://plotly.com/python/) — visualisasi interaktif

---

*Dibangun untuk Divisi Operations & Treasury — Cash Liquidity Optimization for ATM Network.*
