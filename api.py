from fastapi import FastAPI, HTTPException
import requests
from geo_hesaplama import en_iyi_cikislari_bul
from rota_motoru import yurume_rotasi_cek
import uvicorn

app = FastAPI(
    title="SmartExit API - Premium Sürüm",
    description="Metro Çıkış Optimizasyonu, Mapbox Arama ve OSRM Rota Motoru",
    version="3.0.0" # Mapbox mimarisine geçtiğimiz için versiyon atladık!
)

# Kendi Mapbox Token'ın
MAPBOX_TOKEN = "pk.eyJ1IjoieGVvbm9yZXMiLCJhIjoiY21wYXVjOWY1MDBrNDJ0cjJuYjltY3duaCJ9.fh1c6d7kL2NokI_nKwVEJA"

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
        # İŞTE SİHİR BURADA: Sadece mekanları (poi) ve önemli yerleri (place) getir.
        "types": "poi,place,address" 
    }
    
    # EĞER KULLANICI DURAĞINI SEÇMİŞSE: Mapbox'a "Aramaya bu koordinatın etrafından başla" diyoruz.
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
async def cikis_optimize_et(istasyon_adi: str, hat_kodu: str, hedef_lat: float, hedef_lon: float, asansor_sart: bool = False):
    """Adres araması yapmayan, direkt kesin koordinat alan sarsılmaz matematik motorumuz"""
    try:
        # geo_hesaplama'ya artık adresi değil, saf koordinatı ve hat kodunu gönderiyoruz
        oneriler = en_iyi_cikislari_bul(istasyon_adi, hat_kodu, hedef_lat, hedef_lon)
        
        if not oneriler:
             raise HTTPException(status_code=404, detail="Uygun çıkış bulunamadı.")

        en_iyi_kapi = oneriler[0]
        
        # OSRM Motorunu çalıştırıp kapıdan hedefe giden sokak sokak rotayı çekiyoruz
        gercek_rota = yurume_rotasi_cek(
            en_iyi_kapi['gercek_enlem'], 
            en_iyi_kapi['gercek_boylam'], 
            hedef_lat, 
            hedef_lon
        )

        return {
            "durum": "basarili",
            "hedef": {
                "koordinat": {"enlem": hedef_lat, "boylam": hedef_lon}
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
