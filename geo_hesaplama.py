import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests

# Veritabanına kaydederken kullandığımız tuz (şifre) anahtarları
SALT_LAT = 0.0050
SALT_LON = -0.0030

OSRM_URL = "http://localhost:5000"

def istasyon_kapilarini_getir(istasyon_adi: str, hat_kodu: str):
    conn = sqlite3.connect("smartexit.db")
    query = "SELECT * FROM cikislar WHERE istasyon_adi = ? AND hat_kodu = ?"
    df = pd.read_sql_query(query, conn, params=(istasyon_adi, hat_kodu))
    conn.close()

    if df.empty:
        return gpd.GeoDataFrame()

    df['gercek_enlem'] = df['tuzlu_enlem'] - SALT_LAT
    df['gercek_boylam'] = df['tuzlu_boylam'] - SALT_LON

    geometriler = [Point(xy) for xy in zip(df['gercek_boylam'], df['gercek_enlem'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometriler, crs="EPSG:4326")
    return gdf
def tum_cikis_koordinatlarini_getir():
    """Haritada göstermek için tüm çıkışların koordinatlarını döndürür."""
    conn = sqlite3.connect("smartexit.db")
    query = """
    SELECT cikis_id, istasyon_adi, hat_kodu, hat_rengi,
           cikis_no, cikis_adi,
           tuzlu_enlem - 0.0050 as enlem,
           tuzlu_boylam + 0.0030 as boylam
    FROM cikislar
    WHERE tuzlu_enlem IS NOT NULL AND tuzlu_boylam IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    # NaN değerleri 0 ile değiştir
    df = df.fillna(0)
    return df.to_dict('records')

def osrm_table_mesafe(hedef_boylam: float, hedef_enlem: float, cikis_listesi: list) -> list:
    """
    OSRM /table endpoint'i ile tek istekte tüm çıkışların
    hedefe olan gerçek yürüyüş mesafesini hesaplar.
    
    cikis_listesi: [{'gercek_enlem': ..., 'gercek_boylam': ...}, ...]
    Döndürür: her çıkış için metre cinsinden mesafe listesi
    """
    # Koordinatları OSRM formatına çevir: boylam,enlem
    # İlk koordinat hedef, geri kalanlar çıkışlar
    koordinatlar = [f"{hedef_boylam},{hedef_enlem}"]
    for c in cikis_listesi:
        koordinatlar.append(f"{c['gercek_boylam']},{c['gercek_enlem']}")

    koordinat_str = ";".join(koordinatlar)
    
    # sources=1,2,3... (çıkışlar), destinations=0 (hedef)
    cikis_indexler = ";".join(str(i) for i in range(1, len(cikis_listesi) + 1))
    
    url = f"{OSRM_URL}/table/v1/foot/{koordinat_str}"
    params = {
        "sources": cikis_indexler,
        "destinations": "0",
        "annotations": "duration,distance"
    }

    try:
        resp = requests.get(url, params=params, timeout=5)
        veri = resp.json()

        if veri.get("code") == "Ok":
            # distances[i][0] = i. çıkıştan hedefe mesafe (metre)
            distances = veri.get("distances", [])
            return [row[0] if row[0] is not None else 99999 for row in distances]
        else:
            print(f"OSRM table hatası: {veri.get('code')}")
            return None
    except Exception as e:
        print(f"OSRM table bağlantı hatası: {e}")
        return None

def kuş_ucusu_mesafe(lat1, lon1, lat2, lon2):
    """OSRM çalışmazsa yedek olarak kullanılır."""
    import math
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def en_iyi_cikislari_bul(istasyon_adi: str, hat_kodu: str, hedef_enlem: float, hedef_boylam: float):
    """
    Hedef koordinata göre OSRM table endpoint'i ile gerçek yürüyüş
    mesafesini hesaplar ve en yakın Top-3 çıkışı döndürür.
    """
    gdf = istasyon_kapilarini_getir(istasyon_adi, hat_kodu)

    if gdf.empty:
        return []

    cikis_listesi = gdf[['gercek_enlem', 'gercek_boylam']].to_dict('records')

    # OSRM table ile gerçek yürüyüş mesafeleri
    osrm_mesafeler = osrm_table_mesafe(hedef_boylam, hedef_enlem, cikis_listesi)

    if osrm_mesafeler and len(osrm_mesafeler) == len(gdf):
        # OSRM başarılı ise — gerçek mesafeleri kullan
        gdf['mesafe_metre'] = osrm_mesafeler
        print("OSRM table ile gerçek yürüyüş mesafesi kullanıldı.")
    else:
        # OSRM başarısız ise — kuş uçuşuna düş
        print("OSRM table başarısız, kuş uçuşu mesafeye geçildi.")
        gdf['mesafe_metre'] = gdf.apply(
            lambda row: kuş_ucusu_mesafe(row['gercek_enlem'], row['gercek_boylam'], hedef_enlem, hedef_boylam),
            axis=1
        )

    en_yakinlar = gdf.sort_values(by='mesafe_metre').head(3)
    sonuclar = en_yakinlar[['cikis_no', 'cikis_adi', 'mesafe_metre', 'gercek_enlem', 'gercek_boylam']].to_dict('records')
    return sonuclar

def istasyon_duraklarini_getir():
    """Flutter arama ekranında renkli durak listesini ve merkez koordinatlarını verir."""
    conn = sqlite3.connect("smartexit.db")
    query = """
    SELECT istasyon_adi, hat_kodu, hat_rengi,
           AVG(tuzlu_enlem) as tuzlu_enlem,
           AVG(tuzlu_boylam) as tuzlu_boylam
    FROM cikislar
    GROUP BY istasyon_adi, hat_kodu, hat_rengi
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['enlem'] = df['tuzlu_enlem'] - SALT_LAT
    df['boylam'] = df['tuzlu_boylam'] - SALT_LON

    return df[['istasyon_adi', 'hat_kodu', 'hat_rengi', 'enlem', 'boylam']].to_dict('records')

if __name__ == "__main__":
    hedef_lat = 41.0630
    hedef_lon = 28.9930

    print("Hedefe en yakın çıkışlar hesaplanıyor...\n" + "-"*30)

    sonuclar = en_iyi_cikislari_bul("Mecidiyeköy", "M7", hedef_lat, hedef_lon)

    for i, sonuc in enumerate(sonuclar, 1):
        print(f"{i}. Seçenek: {sonuc['cikis_no']} Numaralı Çıkış ({sonuc['cikis_adi']}) -> Yürüme Mesafesi: {sonuc['mesafe_metre']:.1f} metre")
