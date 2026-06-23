from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from geo_hesaplama import en_iyi_cikislari_bul, istasyon_duraklarini_getir, tum_cikis_koordinatlarini_getir
from rota_motoru import yurume_rotasi_cek
import uvicorn
from yerler_api import router as yerler_router
app.include_router(yerler_router)

app = FastAPI(
    title="SmartExit API - Premium Sürüm",
    description="Metro Çıkış Optimizasyonu, Mapbox Arama ve OSRM Rota Motoru",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/istasyonlar")
async def istasyonlari_listele():
    """Flutter açılışta veya kullanıcı yazarken yerel durakları (renkleriyle) dönen sıfır maliyetli link"""
    return istasyon_duraklarini_getir()

@app.get("/api/v1/yer-ara")
async def yer_ara(sorgu: str, user_lat: float = None, user_lon: float = None):
    if not sorgu or len(sorgu) < 2:
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir arama metni girin.")
        
    sonuclar = []
    
    try:
        nom_url = "https://nominatim.openstreetmap.org/search"
        nom_params = {
            "q": sorgu,
            "format": "json",
            "countrycodes": "tr",
            "limit": 5,
            "addressdetails": 1
        }
        if user_lat and user_lon:
            nom_params["viewbox"] = f"{user_lon-0.05},{user_lat+0.05},{user_lon+0.05},{user_lat-0.05}"
            nom_params["bounded"] = 0 
            
        nom_headers = {"User-Agent": "SmartExitApp/3.0 (Premium)"}
        nom_resp = requests.get(nom_url, params=nom_params, headers=nom_headers, timeout=4)
        nom_data = nom_resp.json()
        
        for item in nom_data:
            yer_ismi = item.get("name", item.get("display_name", "").split(",")[0])
            sonuclar.append({
                "yer_ismi": yer_ismi,
                "acik_adres": item.get("display_name"),
                "enlem": float(item["lat"]),
                "boylam": float(item["lon"])
            })
    except Exception as e:
        print(f"Nominatim Motoru Uyarı Verdi: {e}")

    return {"durum": "basarili", "sonuclar": sonuclar[:5]}


@app.get("/api/v1/tum-cikislar")
async def tum_cikislari_getir():
    """Haritada göstermek için tüm çıkış noktalarını döndürür."""
    return tum_cikis_koordinatlarini_getir()


@app.get("/api/v1/en-iyi-cikis")
async def cikis_optimize_et(istasyon_adi: str, hat_kodu: str, hedef_lat: float, gateway_lon: float = None, hedef_lon: float = None, asansor_sart: bool = False):
    """Adres araması yapmayan, direkt kesin koordinat alan sarsılmaz matematik motorumuz"""
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
