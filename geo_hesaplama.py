import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.wkt import loads
from geopy.distance import geodesic

# Veritabanına kaydederken kullandığımız tuz (şifre) anahtarları
SALT_LAT = 0.0050
SALT_LON = -0.0030

def istasyon_kapilarini_getir(istasyon_adi):
    """
    Veritabanından veriyi çeker, tuzlamayı çözer ve Coğrafi Veri Çerçevesine (GeoDataFrame) dönüştürür.
    """
    conn = sqlite3.connect("smartexit.db")
    query = f"SELECT * FROM cikislar WHERE istasyon_adi = '{istasyon_adi}'"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Eğer istasyon bulunamazsa boş bir GeoDataFrame dönelim ki kod patlamasın
    if df.empty:
        return gpd.GeoDataFrame()

    # 2. Tuzdan Arındırma (De-obfuscation)
    df['gercek_enlem'] = df['tuzlu_enlem'] - SALT_LAT
    df['gercek_boylam'] = df['tuzlu_boylam'] - SALT_LON

    # 3. Shapely ile Geometri Oluşturma
    geometriler = [Point(xy) for xy in zip(df['gercek_boylam'], df['gercek_enlem'])]
    
    # 4. GeoPandas'a Dönüştürme
    gdf = gpd.GeoDataFrame(df, geometry=geometriler, crs="EPSG:4326")
    return gdf

def en_iyi_cikislari_bul(istasyon_adi, hedef_enlem, hedef_boylam):
    """
    Hedef koordinata göre istasyondaki en yakın Top-3 çıkışı hesaplar.
    """
    gdf = istasyon_kapilarini_getir(istasyon_adi)
    
    if gdf.empty:
        return []

    hedef_nokta = (hedef_enlem, hedef_boylam)

    # 5. Geodesic Mesafe Hesaplama (WGS-84)
    gdf['mesafe_metre'] = gdf.apply(
        lambda row: geodesic((row['gercek_enlem'], row['gercek_boylam']), hedef_nokta).meters, 
        axis=1
    )

    # 6. Sıralama ve Kesme (Top-3)
    en_yakinlar = gdf.sort_values(by='mesafe_metre').head(3)

    # Yeni sütun isimlerimizi (cikis_no ve cikis_adi) buraya ekledik
    sonuclar = en_yakinlar[['cikis_no', 'cikis_adi', 'mesafe_metre', 'gercek_enlem', 'gercek_boylam']].to_dict('records')
    return sonuclar

if __name__ == "__main__":
    # Test Senaryosu: Mecidiyeköy'den çıktık ve Cevahir AVM'ye (41.0630, 28.9930) gitmek istiyoruz.
    hedef_lat = 41.0630
    hedef_lon = 28.9930
    
    print("Hedefe en yakın çıkışlar hesaplanıyor...\n" + "-"*30)
    
    # "Mecidiyeköy" istasyonunu sorguluyoruz.
    sonuclar = en_iyi_cikislari_bul("Mecidiyeköy", hedef_lat, hedef_lon)
    
    for i, sonuc in enumerate(sonuclar, 1):
        print(f"{i}. Seçenek: {sonuc['cikis_no']} Numaralı Çıkış ({sonuc['cikis_adi']}) -> Yürüme Mesafesi: {sonuc['mesafe_metre']:.1f} metre")
