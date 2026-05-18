import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geopy.distance import geodesic

# Veritabanına kaydederken kullandığımız tuz (şifre) anahtarları
SALT_LAT = 0.0050
SALT_LON = -0.0030

def istasyon_kapilarini_getir(istasyon_adi: str, hat_kodu: str):
    """
    Veritabanından veriyi çeker (Hat kodu filtreli), tuzlamayı çözer ve GeoDataFrame'e dönüştürür.
    """
    conn = sqlite3.connect("smartexit.db")
    # Yenimahalle karışıklığını önlemek için hat_kodu parametresini de SQL sorgusuna ekliyoruz
    query = "SELECT * FROM cikislar WHERE istasyon_adi = ? AND hat_kodu = ?"
    df = pd.read_sql_query(query, conn, params=(istasyon_adi, hat_kodu))
    conn.close()

    # Eğer istasyon/hat bulunamazsa boş bir GeoDataFrame dönelim ki kod patlamasın
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

def en_iyi_cikislari_bul(istasyon_adi: str, hat_kodu: str, hedef_enlem: float, hedef_boylam: float):
    """
    Hedef koordinata göre istasyondaki en yakın Top-3 çıkışı hesaplar.
    """
    gdf = istasyon_kapilarini_getir(istasyon_adi, hat_kodu)
    
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

    # api.py'nin rotayı çizebilmesi için tam olarak bu formata ihtiyacı var
    sonuclar = en_yakinlar[['cikis_no', 'cikis_adi', 'mesafe_metre', 'gercek_enlem', 'gercek_boylam']].to_dict('records')
    return sonuclar

def istasyon_duraklarini_getir():
    """Flutter arama ekranında alttan açılacak renkli durak listesini ve merkez koordinatlarını verir."""
    conn = sqlite3.connect("smartexit.db")
    # Her istasyonun çıkışlarının ortalamasını alarak istasyonun merkez noktasını buluyoruz
    query = """
    SELECT istasyon_adi, hat_kodu, hat_rengi, 
           AVG(tuzlu_enlem) as tuzlu_enlem, 
           AVG(tuzlu_boylam) as tuzlu_boylam 
    FROM cikislar 
    GROUP BY istasyon_adi, hat_kodu, hat_rengi
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Tuzu (şifreyi) çözerek gerçek koordinatları Flutter'a gönderiyoruz
    df['enlem'] = df['tuzlu_enlem'] - SALT_LAT
    df['boylam'] = df['tuzlu_boylam'] - SALT_LON
    
    return df[['istasyon_adi', 'hat_kodu', 'hat_rengi', 'enlem', 'boylam']].to_dict('records')

if __name__ == "__main__":
    # Test Senaryosu: M7 Hattı Mecidiyeköy'den Cevahir AVM'ye (41.0630, 28.9930) gidiş
    hedef_lat = 41.0630
    hedef_lon = 28.9930
    
    print("Hedefe en yakın çıkışlar hesaplanıyor...\n" + "-"*30)
    
    sonuclar = en_iyi_cikislari_bul("Mecidiyeköy", "M7", hedef_lat, hedef_lon)
    
    for i, sonuc in enumerate(sonuclar, 1):
        print(f"{i}. Seçenek: {sonuc['cikis_no']} Numaralı Çıkış ({sonuc['cikis_adi']}) -> Yürüme Mesafesi: {sonuc['mesafe_metre']:.1f} metre")
