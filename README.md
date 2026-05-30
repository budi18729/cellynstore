# Midman Bot — Cellyn Store Community

Bot Discord untuk operasional toko digital. Menangani transaksi middleman trade, middleman jual beli, robux store, topup Mobile Legends & Free Fire, Cloud Phone, Discord Nitro, selfroles, giveaway, welcome, dan admin panel berbasis web.

---

## Fitur

- **Midman Trade** — tiket perantara tukar item antar dua pihak
- **Midman Jual Beli** — tiket perantara jual beli, admin tahan uang pembeli sampai item konfirmasi oke
- **Robux Store** — katalog item Roblox per kategori dengan rate dinamis
- **Robux Via Login (Vilog)** — topup Robux via login akun Roblox (kelipatan 500)
- **Stock Robux** — tampilkan stock tersedia + total robux keluar di catalog (auto update saat transaksi selesai)
- **ML & FF Topup** — topup diamond Mobile Legends, Free Fire, dan Weekly Diamond Pass (WDP)
- **Cloud Phone & Discord Nitro** — order Redfinger cloud phone dan Discord Nitro via tiket
- **Giveaway** — slash command giveaway dengan timer, auto-end, reroll, dan persistent setelah restart
- **Welcome** — welcome/leave/boost notif dengan GIF, auto-assign role Customer saat member join
- **Broadcast** — kirim pengumuman ke channel dengan modal preview, cooldown per admin
- **Auto React** — auto react emoji ke pesan di channel tertentu atau semua pesan admin
- **Server Stats** — voice channel nama otomatis update jumlah member
- **Status Toko (Open/Close)** — voice status otomatis + tombol catalog padam saat toko tutup
- **Selfroles** — self-assignable roles via Discord button
- **AutoPost** — auto-post pesan ke channel Discord via user token, support multiple channel, interval persisten
- **Admin Panel Web** — kelola produk ML/FF/WDP/Robux/Lainnya dan statistik transaksi via browser
- **Statistik Transaksi** — dashboard grafik 7 hari dan 30 hari, produk terlaris, jam tersibuk per layanan
- **Royal Customer** — auto-assign role setelah transaksi sukses di semua layanan
- **Auto-restart** — bot restart otomatis jika crash (max 5x)
- **Warning & Auto-close** — tiket tidak aktif 1 jam dapat peringatan, 2 jam ditutup otomatis
- **Notifikasi URL Admin** — URL Cloudflare Tunnel dikirim ke channel admin setiap bot online

---

## Persyaratan

- Python 3.12+
- Termux (Android) atau Linux
- Akun Discord + Bot Token
- User token Discord untuk AutoPost (opsional)

---

## Setup Awal (Perangkat Baru)

### 1. Clone repo
```bash
git clone https://github.com/EqualityDev/midman.git
cd midman
```

### 2. Buat virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup .env
```bash
cp .env.example .env
nano .env  # isi semua variabel
```

### 5. Jalankan
```bash
bash start.sh
```

`start.sh` otomatis melakukan:
- Cek & pull update terbaru dari GitHub
- Init database SQLite
- Seed data produk default jika DB kosong
- Jalankan admin panel di port 5000
- Install cloudflared jika belum ada
- Jalankan Cloudflare Tunnel (URL dikirim ke Discord)
- Jalankan bot dengan auto-restart

---

## Environment Variables

Salin `.env.example` ke `.env` dan isi semua variabel:

| Variable | Keterangan |
|---|---|
| `TOKEN` | Token bot Discord |
| `GUILD_ID` | ID server Discord |
| `STORE_NAME` | Nama store (tampil di embed) |
| `ADMIN_ROLE_ID` | ID role admin |
| `TICKET_CATEGORY_ID` | ID kategori channel tiket |
| `LOG_CHANNEL_ID` | ID channel log transaksi |
| `TRANSCRIPT_CHANNEL_ID` | ID channel transcript tiket |
| `BACKUP_CHANNEL_ID` | ID channel backup |
| `ERROR_LOG_CHANNEL_ID` | ID channel log error + notifikasi admin panel |
| `MIDMAN_CHANNEL_ID` | ID channel midman |
| `ROBUX_CATALOG_CHANNEL_ID` | ID channel catalog robux |
| `ML_CATALOG_CHANNEL_ID` | ID channel catalog ML/FF |
| `SELFROLES_CHANNEL_ID` | ID channel selfroles |
| `DANA_NUMBER` | Nomor DANA |
| `BCA_NUMBER` | Nomor BCA |
| `TESTIMONI_CHANNEL_ID` | ID channel testimoni |
| `VILOG_CHANNEL_ID` | ID channel log untuk Vilog (opsional) |
| `VILOG_CATALOG_CHANNEL_ID` | ID channel layanan/catalog Vilog |
| `AUTOPOSTER_TOKEN` | User token Discord untuk AutoPost (opsional) |
| `RELAY_SOURCE_CHANNEL_ID` | Source channel relay (opsional) |
| `RELAY_WEBHOOK_URL` | Webhook URL relay (opsional) |

### Opsional (Admin Panel)
| Variable | Default | Keterangan |
|---|---|---|
| `ADMIN_PASSWORD` | `cellyn123` | Password login admin panel |
| `ADMIN_SECRET` | *(auto)* | Secret key Flask session |
| `ADMIN_PORT` | `5000` | Port admin panel |

---

## Admin Panel

Admin panel otomatis jalan saat `bash start.sh`. URL Cloudflare Tunnel dikirim ke `ERROR_LOG_CHANNEL` via embed setiap kali bot online.

Akses: buka URL yang dikirim bot di channel error log → login dengan `ADMIN_PASSWORD`

**Fitur:**
- **Dashboard** — ringkasan produk aktif + update rate Robux
- **ML** — tambah, edit, hapus produk Mobile Legends + Weekly Diamond Pass (WDP)
- **FF** — tambah, edit, hapus produk Free Fire
- **Robux** — tambah, edit, nonaktifkan/aktifkan, hapus item + tambah kategori baru
- **GP Store** — atur rate Garena Point
- **Lainnya** — tambah, edit, nonaktifkan/aktifkan, hapus produk Cloud Phone & Discord Nitro + tambah kategori baru
- **QRIS** — atur rekening QRIS
- **Statistik** — grafik transaksi 7 hari dan 30 hari, produk terlaris, jam tersibuk per layanan
- **AutoPost** — atur auto-post pesan ke channel Discord
- **Info Layanan** — kelola info layanan yang ditampilkan sebelum buka tiket

Perubahan produk via web langsung berlaku ke bot tanpa restart.

---

## Command Reference

### Midman Trade
| Command | Fungsi |
|---|---|
| `!open` | Kirim embed catalog midman |
| `!acc` | Konfirmasi trade selesai |
| `!batal [alasan]` | Batalkan tiket midman |
| `!fee [nominal]` | Hitung fee midman |

### Midman Jual Beli
| Command | Fungsi |
|---|---|
| `!jbuang` | Konfirmasi uang dari pembeli diterima |
| `!jbselesai` | Release dana ke penjual (setelah pembeli konfirmasi item) |
| `!jbbatal [alasan]` | Batalkan tiket jual beli |

### Robux Store
| Command | Fungsi |
|---|---|
| `!catalog` | Kirim embed catalog robux |
| `!rate [angka]` | Set rate Robux |
| `!stock` | Lihat stock robux (tersedia + total keluar) |
| `!stockset [robux]` | Set stock robux tersedia |
| `!stockadd [robux]` | Tambah stock robux tersedia |
| `!stockoutadd [robux]` | Tambah robux keluar (total) tanpa mengurangi stock |
| `!stockoutship [robux]` | Robux keluar + kurangi stock (koreksi manual) |
| `!gift` | Konfirmasi gift item selesai |
| `!tolak [alasan]` | Batalkan tiket robux |

### Robux Via Login (Vilog)
| Command | Fungsi |
|---|---|
| `!vilogcatalog` | Kirim/refresh embed layanan Vilog |
| `!ratevilog [angka]` | Set rate Vilog |
| `!vilogdone` | Konfirmasi Vilog selesai |
| `!vilogbatal [alasan]` | Batalkan tiket Vilog |

### GP Topup (Gamepass)
| Command | Fungsi |
|---|---|
| `!gpcatalog` | Kirim embed catalog GP Topup |
| `!gprate [angka]` | Set rate GP |
| `!gplink [url]` | Kirim link gamepass (opsional) |
| `!gpdone` | Konfirmasi gamepass sudah dibeli (selesai) |
| `!gpbatal [alasan]` | Batalkan tiket GP |

### ML & FF Topup
| Command | Fungsi |
|---|---|
| `!mlcatalog` | Kirim embed catalog ML/FF/WDP |
| `!mlselesai` | Konfirmasi topup selesai |
| `!mlbatal [alasan]` | Batalkan tiket ML/FF |

### Cloud Phone & Discord Nitro
| Command | Fungsi |
|---|---|
| `!lainnya` | Kirim embed katalog Cloud Phone & Nitro |
| `!done` | Tutup tiket sukses |
| `!cancel [alasan]` | Batalkan tiket |

### AutoPost
| Command | Fungsi |
|---|---|
| `!autopost add [#channel] [interval_menit] [pesan]` | Tambah autopost task |
| `!autopost list` | Lihat daftar task |
| `!autopost toggle [id]` | Toggle on/off |
| `!autopost delete [id]` | Hapus task |

### Giveaway
| Command | Fungsi |
|---|---|
| `/giveaway` | Buat giveaway baru |
| `/giveaway_end` | Akhiri giveaway lebih awal |
| `/giveaway_reroll` | Reroll pemenang |
| `/giveaway_list` | Lihat giveaway aktif |

### Welcome & Tools
| Command | Fungsi |
|---|---|
| `/setwelcome` | Atur channel/GIF welcome, boost notif, atau nonaktifkan |
| `/broadcast` | Kirim pengumuman ke channel (modal preview) |
| `/setreact` | Set auto react di channel untuk pesan admin |
| `/setreactall` | Set auto react untuk semua user di channel |
| `/reactlist` | Lihat daftar channel auto react |
| `/setstatschannel` | Set voice channel untuk stats member |
| `/unsetstatschannel` | Nonaktifkan stats channel |

### Lainnya
| Command | Fungsi |
|---|---|
| `!selfroles` | Kirim embed self roles |
| `!cmd` | Tampilkan prefix guide (auto-hapus 10 detik) |
| `!update` | Pull GitHub + restart bot |
| `!ping` | Cek latency |
| `!info` | Info bot |

> Semua command prefix kecuali `!open` hanya bisa digunakan oleh role admin.

---

## Alur Tiket

### Midman Trade
1. Member klik tombol **⚔️ Midman Trade** di channel midman
2. Isi form: item pihak 1 + item yang diminta
3. Admin bergabung, setup pihak 2 + fee
4. Fee dibayar, admin konfirmasi → trade berlangsung
5. Admin ketik `!acc` untuk tutup tiket

### Midman Jual Beli
1. Penjual klik tombol **🛒 Midman Jual Beli** di channel midman
2. Isi form: deskripsi item + harga
3. Admin setup: tambah pembeli, set fee + penanggung fee
4. Pembeli transfer ke admin sesuai nominal
5. Admin ketik `!jbuang` → konfirmasi uang diterima, serahkan item ke pembeli
6. Pembeli klik **✅ Item Diterima & Sesuai**
7. Admin ketik `!jbselesai` → dana direlease ke penjual, tiket ditutup

### Robux Store
1. Member klik kategori di channel catalog robux
2. Pilih item dari dropdown
3. Transfer sesuai nominal + kirim bukti bayar
4. Admin cek bukti bayar (manual), gift item via Roblox
5. Admin ketik `!gift` untuk tutup tiket

### Robux Via Login (Vilog)
1. Member klik **Order** di channel catalog Vilog
2. Isi form (jumlah robux kelipatan 500, email, password, kode backup, premium)
3. Bayar sesuai instruksi admin + kirim bukti bayar
4. Admin proses topup via login
5. Admin ketik `!vilogdone` untuk tutup tiket

### ML & FF Topup
1. Member pilih diamond / WDP di channel catalog ML
2. Isi form: ID ML + Server ID (untuk ML) atau Player ID (untuk FF)
3. Bayar via QRIS
4. Admin proses topup, ketik `!mlselesai`

### Cloud Phone & Discord Nitro
1. Member klik kategori di channel lainnya
2. Pilih item dari dropdown
3. Tiket terbuka, member ketik **1/2/3** untuk pilih metode bayar
4. Bayar sesuai nominal, kirim bukti transfer
5. Admin proses, ketik `!done` untuk tutup tiket

---

## Struktur File

```
midman/
├── main.py               # Entry point bot + notifikasi URL tunnel
├── admin.py              # Flask admin panel (port 5000)
├── admin_embed.py        # Blueprint untuk embed builder
├── seed.py               # Seed data produk default ke DB
├── start.sh              # Auto-start semua service
├── requirements.txt
├── .env.example
├── utils/
│   ├── config.py         # Semua env variable
│   ├── db.py             # init_db() + semua tabel SQLite + log_transaction()
│   ├── counter.py        # Auto-increment nomor tiket
│   ├── transcript.py     # Generate HTML transcript
│   ├── fee.py            # Kalkulator fee midman
│   ├── tickets.py        # CRUD tiket midman trade
│   ├── robux_db.py       # CRUD tiket robux + bot_state
│   ├── robux_stock.py    # Stock robux (tersedia + total keluar)
│   ├── store_hours.py    # Jam operasional (WIB) open/close
│   ├── autoposter_settings.py  # CRUD autopost tasks
│   └── gp_db.py          # CRUD GP (gamepass) topup
└── cogs/
    ├── midman.py         # Midman trade
    ├── jualbeli.py       # Midman jual beli
    ├── robux.py          # Robux store
    ├── vilog.py          # Robux via login (Vilog)
    ├── store_status.py   # Voice status open/close + refresh catalog
    ├── ml.py             # Topup ML, FF & WDP
    ├── lainnya.py        # Cloud Phone & Discord Nitro
    ├── orders.py         # Shared !done & !cancel
    ├── giveaway.py        # Giveaway slash commands
    ├── welcome.py         # Welcome/leave/boost notif + auto role Customer
    ├── broadcast.py       # Broadcast pengumuman dengan cooldown
    ├── auto_react.py      # Auto react emoji per channel
    ├── server_stats.py    # Voice channel stats member count
    ├── selfroles.py       # Self-assignable roles
    ├── testimoni.py       # Auto-reply channel testimoni
    ├── qr.py              # QRIS management
    ├── gp.py              # Topup Robux via Gamepass
    ├── poll.py            # Poll command
    ├── embed_builder.py   # Custom embed builder
    ├── afk.py             # AFK system
    ├── relay.py           # Relay webhook forwarder
    └── views.py           # Shared Discord UI views
```

---

## Database

SQLite (`midman.db`) tidak di-push ke GitHub. Di-generate otomatis saat `bash start.sh`.

**Tabel produk:**
- `ml_products` — produk Mobile Legends
- `wdp_products` — paket Weekly Diamond Pass
- `ff_products` — produk Free Fire
- `robux_products` — item Robux per kategori
- `lainnya_products` — produk Cloud Phone & Discord Nitro

**Tabel transaksi:**
- `tickets` — midman trade
- `jb_tickets` — midman jual beli
- `robux_tickets` — tiket robux
- `gp_tickets` — tiket topup Robux via gamepass
- `vilog_tickets` — tiket topup Robux via login (Vilog)
- `ml_tickets` — tiket ML & FF
- `lainnya_tickets` — tiket Cloud Phone & Nitro
- `transaction_log` — log semua transaksi sukses (untuk statistik)
- `robux_rate` — rate Robux saat ini

**Tabel lainnya:**
- `giveaways` — giveaway aktif
- `auto_react` — channel auto react
- `bot_state` — state bot (embed message ID catalog, welcome settings, broadcast cooldown, dll)
- `autopost_tasks` — task autopost (channel, message, interval, user_token, loop_counter)
- `autopost_history` — history posting autopost

---

## Workflow Development

```
HP (dev) → GitHub → Production via !update di Discord
```

Semua perubahan kode dilakukan di HP, push ke GitHub, lalu `!update` di Discord untuk deploy ke production.

**Catatan:** Folder `data/` (GIF welcome/boost) dan `midman.db` tidak di-track Git. Backup secara berkala.
