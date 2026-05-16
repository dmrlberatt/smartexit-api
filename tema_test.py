import folium

def harita_temalarini_test_et():
    # Şişli Meydanı merkezli boş bir harita oluşturuyoruz
    baslangic_enlem = 41.0628
    baslangic_boylam = 28.9932
    
    # Haritayı oluştururken varsayılan bir tile belirtmiyoruz ki hepsini biz ekleyelim
    harita = folium.Map(location=[baslangic_enlem, baslangic_boylam], zoom_start=15, tiles=None)
    
    # --- ÜCRETSİZ VE DAHİLİ HARİTA ALTLIKLARI (TILES) ---
    
    # 1. Klasik OpenStreetMap (Senin ilk gördüğün, en detaylı ama biraz kalabalık olan)
    folium.TileLayer('OpenStreetMap', name='Klasik (OpenStreetMap)').add_to(harita)
    
    # 2. CartoDB Positron (Açık renkli, minimalist, Uber tarzı açık tema)
    folium.TileLayer('CartoDB positron', name='Açık Tema (CartoDB Positron)').add_to(harita)
    
    # 3. CartoDB Dark Matter (Az önce yazdığımız koyu tema, neon renkler için ideal)
    folium.TileLayer('CartoDB dark_matter', name='Koyu Tema (CartoDB Dark Matter)').add_to(harita)

    # Not: Eskiden "Stamen Toner" ve "Stamen Watercolor" gibi sanatsal haritalar da vardı 
    # ancak yakın zamanda ücretsiz erişimlerini kapattıkları için sisteme eklemedim.

    # Örnek bir işaretçi ekleyelim ki pinlerin nasıl durduğunu da gör
    folium.Marker(
        location=[baslangic_enlem, baslangic_boylam],
        popup="Örnek İstasyon Çıkışı",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(harita)

    # SİHİRLİ KOMUT: Sağ üst köşeye katman seçme menüsünü ekler
    folium.LayerControl().add_to(harita)
    
    dosya_adi = "tema_secici.html"
    harita.save(dosya_adi)
    print(f"Test haritası oluşturuldu! Lütfen tarayıcınızda '{dosya_adi}' dosyasını açın.")

if __name__ == "__main__":
    harita_temalarini_test_et()