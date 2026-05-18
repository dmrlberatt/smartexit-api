from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # YENİ: CORS middleware içeri aktarıldı
import requests
from geo_hesaplama import en_iyi_cikislari_bul, istasyon_duraklarini_getir # YENİ: durak getirme eklendi
from rota_motoru import yurume_rotasi_cek
import uvicorn

app = FastAPI(
    title="SmartExit API - Premium Sürüm",
    description="Metro Çıkış Optimizasyonu, Mapbox Arama ve OSRM Rota Motoru",
    version="3.0.0"
)

# YENİ: Chrome (Web) ve diğer platformların CORS engeline takılmaması için güvenlik izinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Her yerden gelen isteğe izin ver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kendi Mapbox Token'ın
MAPBOX_TOKEN = "pk.eyJ1IjoieGVvbm9yZXMiLCJhIjoiY21wYXVjOWY1MDBrNDJ0cjJuYjltY3duaCJ9.fh1c6d7kL2NokI_nKwVEJA"

# YENİ ENDPOINT: Flutter'ın açılışta veya kullanıcı yazarken pembe/renkli logolarla durakları listelemesini sağlayan fonksiyon
@app.get("/api/v1/istasyonlar")
async def istasyonlari_listele():
    """Flutter açılışta veya kullanıcı yazarken yerel durakları (renkleriyle) dönen sıfır maliyetli link"""
    return istasyon_duraklarini_getir()
@app.get("/api/v1/yer-ara")
async def yer_ara(sorgu: str, user_lat: float = None, user_lon: float = None):
    """Melez Arama Motoru: Önce Nominatim (Mekanlar için), Bulamazsa Mapbox (Sokaklar için)"""
    if not sorgu or len(sorgu) < 2:
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir arama metni girin.")
        
    sonuclar = []
    
    # --- 1. MOTOR: OpenStreetMap (Nominatim) - Türkiye POI'leri için çok daha zeki ---
    try:
        nom_url = "https://nominatim.openstreetmap.org/search"
        nom_params = {
            "q": sorgu,
            "format": "json",
            "countrycodes": "tr",
            "limit": 5,
            "addressdetails": 1
        }
        # Kullanıcının konumunu (Durağı) merkeze alan esnek bir radar (viewbox) kuruyoruz
        if user_lat and user_lon:
            nom_params["viewbox"] = f"{user_lon-0.05},{user_lat+0.05},{user_lon+0.05},{user_lat-0.05}"
            nom_params["bounded"] = 0 
            
        nom_headers = {"User-Agent": "SmartExitApp/3.0 (Premium)"}
        nom_resp = requests.get(nom_url, params=nom_params, headers=nom_headers, timeout=4)
        nom_data = nom_resp.json()
        
        for item in nom_data:
            # Gelen karmaşık veriden sadece temiz mekan ismini ve adresini süzüyoruz
            yer_ismi = item.get("name", item.get("display_name", "").split(",")[0])
            sonuclar.append({
                "yer_ismi": yer_ismi,
                "acik_adres": item.get("display_name"),
                "enlem": float(item["lat"]),
                "boylam": float(item["lon"])
            })
    except Exception as e:
        print(f"Nominatim Motoru Uyarı Verdi: {e}")

    # Eğer Nominatim o mekanı bulduysa doğrudan Flutter'a gönder, Mapbox'a bulaşma
    if sonuclar:
        return {"durum": "basarili", "sonuclar": sonuclar[:5]}
        
    # --- 2. MOTOR (YEDEK): Mapbox Geocoding (Spesifik Sokak/Adres aramaları için) ---
    try:
        mb_url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{sorgu}.json"
        mb_params = {
            "access_token": MAPBOX_TOKEN,
            "country": "tr",
            "limit": 5,
            "language": "tr",
            "types": "poi,place,address" 
        }
        if user_lat and user_lon:
            mb_params["proximity"] = f"{user_lon},{user_lat}"
            
        mb_resp = requests.get(mb_url, params=mb_params, timeout=4)
        mb_data = mb_resp.json()
        
        for feature in mb_data.get("features", []):
            sonuclar.append({
                "yer_ismi": feature.get("text_tr", feature.get("text")),
                "acik_adres": feature.get("place_name_tr", feature.get("place_name")),
                "enlem": feature["geometry"]["coordinates"][1],
                "boylam": feature["geometry"]["coordinates"][0]
            })
        return {"durum": "basarili", "sonuclar": sonuclar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama Motorları Çöktü: {str(e)}")


@app.get("/api/v1/en-iyi-cikis")
async def cikis_optimize_et(istasyon_adi: str, hat_kodu: str, hedef_lat: float, gateway_lon: float = None, hedef_lon: float = None, asansor_sart: bool = False):
    """Adres araması yapmayan, direkt kesin koordinat alan sarsılmaz matematik motorumuz"""
    # Swagger ve test esnekliği için hedef_lon parametresini kontrol altına alıyoruz
    lon = hedef_lon if hedef_lon is not None else gateway_lon
    if lon is None:
        raise HTTPException(status_code=400, detail="hedef_lon parametresi eksik.")
        
    try:
        oneriler = en_iyi_cikislari_bul(istasyon_adi, hat_kodu, hedef_lat, lon)
        
        if not oneriler:
             raise HTTPException(status_code=404, detail="Uygun çıkış bulunamadı.")

        en_iyi_kapi = oneriler[0]
        
        gercek_rota = yurume_rotasi_cek(
            en_iyi_kapi['gercek_enlem'], 
            en_iyi_kapi['gercek_boylam'], 
            hedef_lat, 
            lon
        )

        return {
            "durum": "basarili",
            "hedef": {
                "koordinat": {"enlem": hedef_lat, "boylam": lon}
            },
            "en_iyi_cikis": {
                "cikis_numarasi": en_iyi_kapi['cikis_no'],
                "kapi_ismi": en_iyi_kapi['cikis_adi'],
                "mesafe_metre": round(en_iyi_kapi['mesafe_metre'], 1),
                "asansorlu_mu": en_iyi_kapi.get('asansor_var_mi', False)
            },
            "yurume_rotasi_koordinatlari": gercek_rota,
            "diger_alternatif_cikislar": oneriler[1:]
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem Hatası: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
