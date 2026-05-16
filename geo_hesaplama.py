import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geopy.distance import geodesic

# Veritabanına kaydederken kullandığımız tuz (şifre) anahtarları
SALT_LAT = 0.0050
SALT_LON = -0.0030

def istasyon_kapilarini_getir(istasyon_id):
    """
    Veritabanından veriyi çeker, tuzlamayı çözer ve Coğrafi Veri Çerçevesine (GeoDataFrame) dönüştürür.
    """
    # 1. Veriyi Pandas ile Okuma
    # Pandas, verileri Excel tablosu gibi hafızada tutmamızı sağlayan harika bir kütüphanedir.
    conn = sqlite3.connect("smartexit.db")
    query = f"SELECT * FROM kapilar WHERE istasyon_id = '{istasyon_id}'"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # 2. Tuzdan Arındırma (De-obfuscation) - Vektörel İşlem!
    # Python'da 'for' döngüsü yazmak yerine tüm sütundan tuzu tek seferde çıkarıyoruz. (Çok daha hızlıdır)
    df['gercek_enlem'] = df['tuzlu_enlem'] - SALT_LAT
    df['gercek_boylam'] = df['tuzlu_boylam'] - SALT_LON

    # 3. Shapely ile Geometri Oluşturma
    # Harita işlemleri yapabilmek için enlem ve boylamı bir "Nokta (Point)" objesine çevirmeliyiz.
    # zip() fonksiyonu enlem ve boylam listelerini fermuar gibi birbirine bağlar.
    geometriler = [Point(xy) for xy in zip(df['gercek_boylam'], df['gercek_enlem'])]
    
    # 4. GeoPandas'a Dönüştürme
    # Artık elimizde WGS-84 (EPSG:4326) sistemine uyumlu bir coğrafi veri tablosu var.
    gdf = gpd.GeoDataFrame(df, geometry=geometriler, crs="EPSG:4326")
    return gdf

def en_iyi_cikislari_bul(istasyon_id, hedef_enlem, hedef_boylam, asansor_sart=False):
    """
    Hedef koordinata göre istasyondaki en yakın Top-3 çıkışı hesaplar.
    """
    gdf = istasyon_kapilarini_getir(istasyon_id)
    hedef_nokta = (hedef_enlem, hedef_boylam)

    # Pandas Filtrelemesi: Eğer asansör şartı varsa, tablodan sadece asansörlü olanları ayır.
    if asansor_sart:
        gdf = gdf[gdf['asansor_var_mi'] == 1]

    # 5. Geodesic Mesafe Hesaplama (WGS-84)
    # apply() fonksiyonu tablodaki her satır için belirlediğimiz işlemi (lambda) uygular.
    # geodesic(), dünyanın tam yuvarlak olmadığını (kutuplardan basık olduğunu) hesaba katarak en hassas ölçümü yapar.
    gdf['mesafe_metre'] = gdf.apply(
        lambda row: geodesic((row['gercek_enlem'], row['gercek_boylam']), hedef_nokta).meters, 
        axis=1
    )

    # 6. Sıralama ve Kesme (Top-3)
    # Mesafeye göre küçükten büyüğe sırala ve en üstteki 3 tanesini (head) al.
    en_yakinlar = gdf.sort_values(by='mesafe_metre').head(3)

    # API'nin (FastAPI) kolayca anlayabileceği bir sözlük (dictionary) listesine çevirip döndürüyoruz.
    # Yeni sütun isimlerimizi (cikis_numarasi ve kapi_ismi) buraya ekledik
    # Yeni Hal: Kapının gerçek koordinatlarını da dışarı veriyoruz ki OSRM rota çizebilsin
    sonuclar = en_yakinlar[['cikis_numarasi', 'kapi_ismi', 'mesafe_metre', 'asansor_var_mi', 'gercek_enlem', 'gercek_boylam']].to_dict('records')
    return sonuclar

# Script test bloğu
if __name__ == "__main__":
    # Test Senaryosu: Şişli metrosundan çıktık ve Cevahir AVM'ye (41.0630, 28.9930) gitmek istiyoruz.
    hedef_lat = 41.0630
    hedef_lon = 28.9930
    
    print("Hedefe en yakın çıkışlar hesaplanıyor...\n" + "-"*30)
    
    # Önceki kodda eklediğimiz "m2_sisli" istasyonunu sorguluyoruz.
    sonuclar = en_iyi_cikislari_bul("m2_sisli", hedef_lat, hedef_lon)
    
    for i, sonuc in enumerate(sonuclar, 1):
        # Artık hem çıkış numarasını hem de kapı ismini ekrana yazdırıyoruz
        print(f"{i}. Seçenek: {sonuc['cikis_numarasi']} Numaralı Çıkış ({sonuc['kapi_ismi']}) -> Yürüme Mesafesi: {sonuc['mesafe_metre']:.1f} metre")