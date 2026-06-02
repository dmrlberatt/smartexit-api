from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # CORS middleware içeri aktarıldı
import requests
from geo_hesaplama import en_iyi_cikislari_bul, istasyon_duraklarini_getir, tum_cikis_koordinatlarini_getir
from rota_motoru import yurume_rotasi_cek
import uvicorn

app = FastAPI(
    title="SmartExit API - Premium Sürüm",
    description="Metro Çıkış Optimizasyonu, Photon Arama ve OSRM Rota Motoru",
    version="3.0.0"
)

#  Chrome (Web) ve diğer platformların CORS engeline takılmaması için güvenlik izinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Her yerden gelen isteğe izin ver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ENDPOINT: Flutter'ın açılışta veya kullanıcı yazarken pembe/renkli logolarla durakları listelemesini sağlayan fonksiyon
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
        # Konum gelmezse İstanbul merkezli önceliklendiriyoruz
        lat = user_lat if user_lat is not None else 41.0082
        lon = user_lon if user_lon is not None else 28.9784
        
        # Photon Public API parametreleri
        photon_url = "https://photon.komoot.io/api"
        photon_params = {
            "q": sorgu,
            "lat": lat,
            "lon": lon,
            "limit": 10,
            "lang": "tr"
        }
            
        nom_headers = {"User-Agent": "SmartExitApp/3.0 (Premium)"}
        resp = requests.get(photon_url, params=photon_params, headers=nom_headers, timeout=4)
        
        if resp.status_code == 200:
            photon_data = resp.json()
            
            for feature in photon_data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                coordinates = geometry.get("coordinates", [0.0, 0.0]) # [lon, lat] döner
                
                isim = properties.get("name", "")
                street = properties.get("street", "")
                district = properties.get("district", "") # İlçe
                city = properties.get("city", "")         # Şehir
                
                if not isim or not str(isim).strip():
                    isim = street if street else "Belirsiz Nokta"
                
                detay_parcalari = [district, city]
                detay = ", ".join(filter(None, detay_parcalari))
                if not detay:
                    detay = "İstanbul"
                
                # Flutter'daki SearchResult.fromJson modelinin tam istediği key'ler
                sonuclar.append({
                    "isim": isim,
                    "detay": detay,
                    "lat": coordinates[1], # enlem
                    "lon": coordinates[0]  # boylam
                })
    except Exception as e:
        print(f"Photon Motoru Uyarı Verdi: {e}")

    return {"durum": "basarili", "sonuclar": sonuclar[:5]}

@app.get("/api/v1/tum-cikislar")
async def tum_cikislari_getir():
    """Haritada göstermek için tüm çıkış noktalarını döndürür."""
    return tum_cikis_koordinatlarini_getir()


@app.get("/api/v1/en-iyi-cikis")
async def cikis_optimize_et(istasyon_adi: str, hat_kodu: str, hedef_lat: float, gateway_lon: float = None, hedef_lon: float = None, asansor_sart: bool = False):
    """Adres araması yapmayan, direkt kesin koordinat alan sarsılmaz matematik motorumuz"""
    # Swagger ve test esnekliği için hedef_lon parametresini kontrol altına alıyoruz
    lon = hedef_lon if hedef_lon is not None else gateway_lon
    if lon is None:
        raise HTTPException(status_code=400, detail="hedef_lon parametresi eksik.")
        
    try:
        # İLK KODUNDAKİ PARAMETRE YAPISI VE SIRALAMASI BİREBİR KORUNDU
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
                "koordinat": {"enlem": thresholds_lat if 'thresholds_lat' in locals() else hedef_lat, "boylam": lon}
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
