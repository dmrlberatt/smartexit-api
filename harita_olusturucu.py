import folium
import requests

def rota_ve_harita_olustur(baslangic_enlem, baslangic_boylam, hedef_enlem, hedef_boylam, kapi_ismi):
    """
    OSRM kullanarak iki nokta arasındaki yürüme rotasını hesaplar 
    ve Folium ile interaktif bir harita (HTML) oluşturur.
    """
    print("OSRM üzerinden gerçek yürüme rotası çekiliyor...")
    
    # 1. OSRM API'sine İstek Atıyoruz (Yürüme profili: 'foot')
    # Dikkat: OSRM API koordinatları (boylam, enlem) sırasıyla ister!
    osrm_url = f"http://router.project-osrm.org/route/v1/foot/{baslangic_boylam},{baslangic_enlem};{hedef_boylam},{hedef_enlem}?overview=full&geometries=geojson"
    
    response = requests.get(osrm_url)
    veri = response.json()
    
    if response.status_code != 200 or veri.get("code") != "Ok":
        print("Rota bulunamadı!")
        return None

    # 2. Rota Koordinatlarını Al (GeoJSON formatında geliyor)
    rota_koordinatlari = veri["routes"][0]["geometry"]["coordinates"]
    
    # Folium (Enlem, Boylam) sırasını sevdiği için ters çeviriyoruz
    folium_rotasi = [(lat, lon) for lon, lat in rota_koordinatlari]
    
    # 3. Haritayı Oluştur (Modern ve Koyu Tema)
    harita = folium.Map(
        location=[baslangic_enlem, baslangic_boylam], 
        zoom_start=16,
        tiles="cartodbdark_matter"  # <--- SİHİRLİ DOKUNUŞ BURASI
    )
    
    # 4. Metro Kapısı İşaretçisi (Koyu temada patlasın diye renkleri ayarlayabiliriz)
    folium.Marker(
        location=[baslangic_enlem, baslangic_boylam],
        popup=f"🚇 Başlangıç: {kapi_ismi}",
        icon=folium.Icon(color="green", icon="info-sign")
    ).add_to(harita)
    
    # ... Hedef noktası aynı kalabilir ...
    folium.Marker(
        location=[hedef_enlem, hedef_boylam],
        popup="🎯 Hedefiniz",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(harita)
    
    # 6. Rotayı Çiz (Koyu temada neon mavi çok şık durur)
    folium.PolyLine(
        locations=folium_rotasi,
        color="#00E5FF", # Neon Turkuaz/Mavi
        weight=5,
        opacity=0.9,
        tooltip="Yürüme Rotası"
    ).add_to(harita)
    
    # 7. Haritayı HTML dosyası olarak kaydet
    dosya_adi = "smartexit_rotasi.html"
    harita.save(dosya_adi)
    print(f"Harita başarıyla oluşturuldu! Lütfen tarayıcınızda '{dosya_adi}' dosyasını açın.")

# Test Bloğu
if __name__ == "__main__":
    # Test Senaryosu: Şişli Camii Çıkışından (Başlangıç) -> Cevahir AVM'ye (Hedef)
    # Kapı koordinatları (Veritabanındaki gerçek halleri)
    kapi_lat = 41.0628
    kapi_lon = 28.9932
    
    # Hedef koordinatları (Nominatim'den dönen)
    hedef_lat = 41.0626036
    hedef_lon = 28.9929943
    
    rota_ve_harita_olustur(kapi_lat, kapi_lon, hedef_lat, hedef_lon, "1 Numaralı Çıkış")