from fastapi import FastAPI, HTTPException
from geopy.geocoders import Nominatim
from geo_hesaplama import en_iyi_cikislari_bul
from rota_motoru import yurume_rotasi_cek  # YENİ EKLENDİ
import uvicorn

app = FastAPI(
    title="SmartExit API",
    description="Metro Çıkış Optimizasyonu ve Rota Motoru",
    version="2.0.0" # Rota motoru eklendiği için versiyon atladık!
)

geolocator = Nominatim(user_agent="smartexit_python_ogrencisi")

@app.get("/api/v1/en-iyi-cikis")
async def cikis_optimize_et(istasyon_id: str, hedef_adres: str, asansor_sart: bool = False):
    try:
        lokasyon = geolocator.geocode(
            hedef_adres,
            viewbox=[(41.3, 28.4), (40.7, 29.5)], 
            bounded=True
        )
        
        if not lokasyon:
            raise HTTPException(status_code=404, detail="Adres bulunamadı.")
            
        hedef_enlem = lokasyon.latitude
        hedef_boylam = lokasyon.longitude
        
        oneriler = en_iyi_cikislari_bul(istasyon_id, hedef_enlem, hedef_boylam, asansor_sart)
        
        if not oneriler:
             raise HTTPException(status_code=404, detail="Uygun çıkış bulunamadı.")

        # --- YENİ EKLENEN ROTA BÖLÜMÜ ---
        # Sistemimiz en yakın 3 kapıyı buldu. Biz 1. sıradaki (en mantıklı) kapıyı seçiyoruz.
        en_iyi_kapi = oneriler[0]
        
        # OSRM Motorunu çalıştırıp kapıdan hedefe giden sokak sokak rotayı çekiyoruz
        gercek_rota = yurume_rotasi_cek(
            en_iyi_kapi['gercek_enlem'], 
            en_iyi_kapi['gercek_boylam'], 
            hedef_enlem, 
            hedef_boylam
        )
        # --------------------------------

        return {
            "durum": "basarili",
            "hedef": {
                "adres": lokasyon.address,
                "koordinat": {"enlem": hedef_enlem, "boylam": hedef_boylam}
            },
            "en_iyi_cikis": {
                "cikis_numarasi": en_iyi_kapi['cikis_numarasi'],
                "kapi_ismi": en_iyi_kapi['kapi_ismi'],
                "mesafe_metre": round(en_iyi_kapi['mesafe_metre'], 1),
                "asansorlu_mu": bool(en_iyi_kapi['asansor_var_mi'])
            },
            # API'yi kullanan mobil uygulama bu dizi ile haritaya mavi çizgisini çizecek!
            "yurume_rotasi_koordinatlari": gercek_rota, 
            "diger_alternatif_cikislar": oneriler[1:] # Geri kalan 2 kapıyı alternatif olarak veriyoruz
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem Hatası: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)