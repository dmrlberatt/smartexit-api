import requests

def yurume_rotasi_cek(baslangic_enlem, baslangic_boylam, hedef_enlem, hedef_boylam):
    """
    OSRM API'sine bağlanır ve iki nokta arasındaki yürüme yolunun 
    tüm viraj ve dönemeç koordinatlarını bir liste olarak döndürür.
    """
    # OSRM koordinatları (Boylam, Enlem) formatında ister
    url = f"http://router.project-osrm.org/route/v1/foot/{baslangic_boylam},{baslangic_enlem};{hedef_boylam},{hedef_enlem}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(url, timeout=5)
        veri = response.json()
        
        if response.status_code == 200 and veri.get("code") == "Ok":
            # OSRM'den gelen veriyi alıyoruz
            rota_koordinatlari = veri["routes"][0]["geometry"]["coordinates"]
            
            # Mobil uygulamaların kolay okuması için (Enlem, Boylam) sözlüklerine çeviriyoruz
            formatli_rota = [{"enlem": lat, "boylam": lon} for lon, lat in rota_koordinatlari]
            return formatli_rota
        else:
            return [] # Rota bulunamazsa boş liste dön
    except Exception as e:
        print(f"OSRM Bağlantı Hatası: {e}")
        return []