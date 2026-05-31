# ExIST - İstanbul Metro Çıkış Optimizasyon Uygulaması

## 📱 Proje Açıklaması

ExIST (Exit Smart Istanbul), İstanbul metrosu kullanıcılarının doğru metro çıkışını bulmasını ve yürüyüş rotasını göstermesini sağlayan mobil uygulamadır.

**Ana Özellikler:**
- 89 metro istasyonu ve 266 çıkış noktası veritabanı
- OSRM ile gerçek yürüyüş mesafesi hesabı (kuş uçuşu değil)
- Hedef adresine göre en uygun çıkışı otomatik bulma
- Harita üzerinde rota gösterimi ve animasyonu
- Gizlilik-odaklı tasarım (koordinat tuzlama)
- Çevrimdışı harita desteği
- Google Maps entegrasyonu ile canlı navigasyon

**Kullanıcı Senaryosu:**
```
Kullanıcı Taksim istasyondan Beşiktaş'taki bir mağazaya gitmek istiyor
↓
Uygulamaya "Taksim istasyonu" ve "Mağaza adresi" giriyor
↓
Uygulama 266 çıkış arasından en yakın olanı bulur (örn: Çıkış-14)
↓
Haritada rota gösterilir
↓
Google Maps'te canlı navigasyon yapabilir
```

---

## 🛠 Teknolojiler

### Frontend
- **Dil**: Dart 3.11+
- **Framework**: Flutter 3.16+
- **Harita**: flutter_map + CartoDB tiles
- **Konum**: geolocator + permission_handler
- **Veri Depolama**: shared_preferences, SQLite (local)

### Backend
- **Dil**: Python 3.10+
- **Framework**: FastAPI
- **Veritabanı**: SQLite
- **ORM**: SQLAlchemy
- **Rota Motoru**: OSRM (Open Source Routing Machine)

### İnfrastruktur
- **Sunucu**: DigitalOcean VPS (Ubuntu 24)
- **Domain**: ehliyettamam.app
- **SSL**: Let's Encrypt + Nginx
- **Containerization**: Docker (OSRM için)

---

## 📋 Sistem Gereksinimleri

### Geliştirme Ortamı (Desktop)
- Windows, macOS, veya Linux
- Flutter SDK 3.16+
- Dart SDK 3.11+
- Android Studio (APK build için)
- VS Code + Dart/Flutter extensions
- Git

### Mobil Cihaz (Çalıştırma)
**Minimum:**
- Android 7.0 (API Level 24)
- RAM: 256 MB
- Depolama: 50 MB

**Önerilen:**
- Android 11+
- RAM: 1 GB+
- 4G/5G veya WiFi bağlantısı

### Backend (Sunucu)
- Ubuntu 20.04 LTS+
- Python 3.10+
- PostgreSQL veya SQLite
- Docker (OSRM container için)
- 2 GB RAM, 10 GB depolama

---

## 📦 Kurulum Adımları

### 1️⃣ Projeyi Klonlama

```bash
# Backend
git clone https://github.com/dmrlberatt/smartexit-api.git
cd smartexit-api

# Frontend (örnek)
git clone <flutter-repo-url>
cd smartexit-flutter
```

### 2️⃣ Backend Kurulumu

```bash
# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# veya
venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasını düzenle: API anahtarları, veritabanı bağlantıları, vb.

# Veritabanını başlat
python database_builder.py

# Sunucuyu başlat
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**API Endpoints:**
```
GET  /api/stations           # Tüm istasyonları getir
GET  /api/stations/{id}      # Belirli istasyonu getir
GET  /api/exits?station_id=1 # Bir istasyondaki çıkışları getir
POST /api/route              # Rota hesapla (body: start, end)
GET  /api/search?q=Taksim    # Adres arama (Nominatim)
```

### 3️⃣ OSRM Sunucusu Kurulumu

```bash
# Docker ile OSRM (İstanbul verisi ile)
docker run -t -v /data:/data osrm/osrm-backend osrm-extract -p /opt/osrm-profiles/car.lua /data/turkey-latest.osm.pbf
docker run -t -v /data:/data osrm/osrm-backend osrm-prepare -p /opt/osrm-profiles/car.lua /data/turkey-latest.osm.pbf
docker run -t -i -p 5000:5000 -v /data:/data osrm/osrm-backend osrm-routed --algorithm mld /data/turkey-latest.osm
```

OSRM API: `http://localhost:5000/route/v1/foot/{lon1},{lat1};{lon2},{lat2}`

### 4️⃣ Flutter Frontend Kurulumu

```bash
# Bağımlılıkları al
flutter pub get

# Android emülatörü başlat veya cihazı bağla
flutter devices

# Uygulamayı çalıştır
flutter run

# Release APK oluştur
flutter build apk --release
```

**İmportant Files:**
- `lib/screens/map_screen.dart` - Ana harita ekranı
- `lib/screens/onboarding_screen.dart` - İlk açılış ekranı
- `lib/services/location_service.dart` - Konum takibi
- `lib/services/route_service.dart` - OSRM entegrasyonu
- `lib/services/api_service.dart` - Backend iletişimi

---

## 🚀 Çalıştırma Talimatları

### Geliştirme Ortamında

**Backend:**
```bash
cd smartexit-api
source venv/bin/activate
uvicorn main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

**Frontend:**
```bash
cd smartexit-flutter
flutter run -d android  # Emülatörde
flutter run -d <device-id>  # Fiziksel cihazda
```

### Production Sunucu'da

**systemd Service:**
```bash
# /etc/systemd/system/smartexit.service
[Unit]
Description=ExIST Metro Backend
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=/root/smartexit-api
ExecStart=/root/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl start smartexit
sudo systemctl enable smartexit
sudo systemctl status smartexit
```

**Nginx Reverse Proxy:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.ehliyettamam.app;
    
    ssl_certificate /etc/letsencrypt/live/ehliyettamam.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ehliyettamam.app/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 📂 Proje Yapısı

```
smartexit-api/
├── main.py                 # FastAPI ana dosyası
├── database_builder.py     # Veritabanı oluşturma scripti
├── models/
│   ├── station.py         # MetroStation modeli
│   ├── exit.py            # MetroExit modeli
│   └── route.py           # Rota modeli
├── routes/
│   ├── stations.py        # /api/stations endpoints
│   ├── exits.py           # /api/exits endpoints
│   └── routes.py          # /api/route endpoint
├── services/
│   ├── osrm_service.py    # OSRM entegrasyonu
│   ├── geocoding.py       # Nominatim entegrasyonu
│   └── database.py        # Veritabanı işlemleri
├── data/
│   └── smartexit.db       # SQLite veritabanı
├── requirements.txt
└── .env.example

smartexit-flutter/
├── lib/
│   ├── main.dart          # Ana entry point
│   ├── screens/
│   │   ├── map_screen.dart
│   │   ├── onboarding_screen.dart
│   │   └── splash_screen.dart
│   ├── services/
│   │   ├── api_service.dart
│   │   ├── location_service.dart
│   │   └── route_service.dart
│   ├── models/
│   │   ├── station.dart
│   │   ├── exit.dart
│   │   └── route.dart
│   ├── widgets/
│   │   ├── exit_marker.dart
│   │   ├── result_sheet.dart
│   │   └── theme_selector.dart
│   └── utils/
│       ├── colors.dart
│       ├── constants.dart
│       └── coordinate_helper.dart
├── assets/
│   ├── geojson/
│   │   └── metro_lines.geojson
│   └── fonts/
├── pubspec.yaml
└── android/
    ├── app/
    │   └── build.gradle
    └── gradle.properties
```

---

## 🔑 Önemli Ayarlar

### Koordinat Tuzlama (Privacy)
```python
# backend/services/database.py
SALT_LAT = 0.005
SALT_LON = -0.003

# Gerçek koordinat = DB koordinat + tuz
actual_lat = db_lat + SALT_LAT
actual_lon = db_lon + SALT_LON
```

### API Base URL
```dart
// lib/services/api_service.dart
const String baseUrl = 'https://api.ehliyettamam.app';
const String osrmUrl = 'http://68.183.15.171:5000';
```

### Metro Hatları (Assets)
```dart
// lib/assets/geojson/metro_lines.geojson
// İçerir: M1A, M2, M3, M4, M5, M7, M8, M11, B1
```

---

## 🧪 Test Etme

### Backend API Test (Postman)
```
POST http://localhost:8000/api/route
Body (JSON):
{
  "start": {"lat": 41.0082, "lon": 28.9784},
  "end": {"lat": 41.0365, "lon": 28.9894},
  "station_id": 1
}
```

### Flutter Widget Test
```bash
flutter test test/widget_test.dart
```

### OSRM Test
```bash
curl "http://localhost:5000/route/v1/foot/28.9784,41.0082;28.9894,41.0365?overview=full&geometries=geojson"
```

---

## 📊 Veri Yapısı

### MetroStation (89 toplam)
```json
{
  "id": "1",
  "name": "Taksim",
  "line": "M2",
  "latitude": 41.0372,
  "longitude": 28.9851,
  "exits_count": 4
}
```

### MetroExit (266 toplam)
```json
{
  "id": "1A",
  "name": "Taksim Square",
  "station_id": "1",
  "exit_number": 1,
  "latitude": 41.03725,
  "longitude": 28.98515,
  "direction": "North"
}
```

---

## 🐛 Bilinen Sorunlar ve Çözümler

| Sorun | Nedeni | Çözüm |
|-------|--------|-------|
| Konum izni alınmıyor | Android 12+ permission_handler | AppSettings.openAppSettings() çağır |
| Rota hesabı yavaş | 266 çıkış arasından tam arama | Station ID'ye göre filtrele (backend) |
| Harita lag yaşanıyor | Zoom seviyesinde çok sayıda marker | Zoom level 15'de marker göster |
| Koordinat yanlış yerde | LAT/LON karışıklığı | CoordinateHelper.toLatLng() kullan |

---

## 📱 Play Store Yayını

### APK Oluşturma
```bash
flutter build apk --release
# Output: build/app/outputs/apk/release/app-release.apk
```

**Play Store Metadata:**
- Paket Adı: `com.beratdemirel.exist`
- Version Code: 1
- Version Name: 1.0.0
- Minimum SDK: 24 (Android 7.0)
- Target SDK: 34 (Android 14)

---


---


## 👨‍💻 Proje Sahibi

**Berat Demirel**
- GitHub: [@dmrlberatt](https://github.com/dmrlberatt)


