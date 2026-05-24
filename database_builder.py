import sqlite3
import pandas as pd
from shapely.wkt import loads

# Güvenlik Hendeği (Tuzlama) Değerleri
SALT_LAT = 0.0050
SALT_LON = -0.0030

def veritabani_olustur():
    conn = sqlite3.connect("smartexit.db")
    cursor = conn.cursor()
    
    # Yeni ve güvenli tablomuzu oluşturuyoruz
    cursor.execute("DROP TABLE IF EXISTS cikislar")
    cursor.execute('''
        CREATE TABLE cikislar (
            cikis_id TEXT PRIMARY KEY,
            istasyon_adi TEXT NOT NULL,
            hat_kodu TEXT,
            hat_rengi TEXT,
            cikis_no INTEGER,
            tuzlu_enlem REAL NOT NULL,
            tuzlu_boylam REAL NOT NULL,
            cikis_adi TEXT
        )
    ''')
    
    # Yeni formatlı CSV dosyanı okuyoruz
    df = pd.read_csv("kapilar.csv")
    # Sütun isimlerindeki o sinsi boşlukları otomatik temizle!
    df.columns = df.columns.str.strip()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)  # Değerleri de temizle
    
    # Her bir satırı dönüp POINT formatını parçalıyor ve tuzluyoruz
    for index, row in df.iterrows():
        # POINT(boylam enlem) yapısını shapely ile okuyoruz
        temiz_koordinat = str(row["koordinat"]).replace('"', '').strip()
        geometri = loads(temiz_koordinat)
        gercek_boylam = geometri.x
        gercek_enlem = geometri.y
        
        # Koordinatları tuzluyoruz
        gizli_enlem = gercek_enlem + SALT_LAT
        gizli_boylam = gercek_boylam + SALT_LON
        
        # Veritabanına şifrelenmiş haliyle ve hat logolarıyla kaydediyoruz
        cursor.execute('''
            INSERT OR REPLACE INTO cikislar (cikis_id, istasyon_adi, hat_kodu, hat_rengi, cikis_no, tuzlu_enlem, tuzlu_boylam, cikis_adi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row["cikis_id"], 
            row["istasyon_adi"], 
            row["hat_kodu"], 
            str(row["hat_rengi"]).strip(),  # <-- BOŞLUKLARI SİLEN SİHİRLİ KOD BURADA
            row["cikis_no"], 
            gizli_enlem, 
            gizli_boylam,
            row["cikis_adi"]
        ))
    
    conn.commit()
    conn.close()
    print("Sadeleştirilmiş CSV (POINT formatı), hat renkleri ve tuzlama katmanıyla veritabanına başarıyla kaydedildi!")

if __name__ == "__main__":
    veritabani_olustur()
