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
    """Mapbox tabanlı, konuma duyarlı akıllı arama"""
    if not sorgu or len(sorgu) < 2:
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir arama metni girin.")
        
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{sorgu}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "tr",
        "bbox": "27.95,40.80,29.95,41.60", 
        "limit": 5,
        "language": "tr",
        "types": "poi,place,address" 
    }
    
    if user_lat and user_lon:
        params["proximity"] = f"{user_lon},{user_lat}"
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        sonuclar = []
        for feature in data.get("features", []):
            sonuclar.append({
                "yer_ismi": feature.get("text_tr", feature.get("text")),
                "acik_adres": feature.get("place_name_tr", feature.get("place_name")),
                "enlem": feature["geometry"]["coordinates"][1],
                "boylam": feature["geometry"]["coordinates"][0]
            })
        return {"durum": "basarili", "sonuclar": sonuclar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mapbox Arama Motoru Hatası: {str(e)}")


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
