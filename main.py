from fastapi import FastAPI, HTTPException, Query
from geopy.geocoders import Nominatim
from geo_hesaplama import en_iyi_cikislari_bul
import uvicorn

app = FastAPI(
    title="SmartExit API",
    description="Metro Çıkış Optimizasyonu ve Karar Destek Sistemi",
    version="1.0.0"
)

# User-agent Nominatim politikaları için zorunludur
geolocator = Nominatim(user_agent="smartexit_application")

@app.get("/api/v1/optimize")
async def optimize_exit(
    station_id: str = Query(..., description="Mevcut metro istasyon ID'si (Örn: m4_kadikoy)"),
    target_address: str = Query(..., description="Gitmek istenen hedef adres veya yer adı"),
    require_elevator: bool = Query(False, description="Sadece asansörlü çıkışları filtrele")
):
    try:
        # 1. Geocoding: Adresi Koordinata Çevirme (İstanbul Viewbox'ı ile sınırlandırılmış örnek)
        # Gerçek üretimde viewbox dinamik olarak şehre göre seçilebilir.
        location = geolocator.geocode(
            target_address,
            viewbox=[(41.3, 28.4), (40.7, 29.5)], # İstanbul için daraltılmış arama alanı
            bounded=True
        )
        
        if not location:
            raise HTTPException(status_code=404, detail="Hedef adres koordinatları bulunamadı.")
        
        target_coords = (location.latitude, location.longitude)
        
        # 2. Optimizasyon Motorunu Çalıştır
        suggestions = en_iyi_cikislari_bul(station_id, target_coords, require_elevator)
        
        return {
            "status": "success",
            "searched_address": location.address,
            "target_coordinates": {"lat": location.latitude, "lon": location.longitude},
            "recommendations": suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem hatası: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)