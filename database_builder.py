import sqlite3

SALT_LAT = 0.0050
SALT_LON = -0.0030

def veritabani_olustur():
    conn = sqlite3.connect("smartexit.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS istasyonlar (
            id TEXT PRIMARY KEY,
            isim TEXT NOT NULL,
            sehir TEXT NOT NULL
        )
    ''')
    
    cursor.execute('DROP TABLE IF EXISTS kapilar')
    cursor.execute('''
        CREATE TABLE kapilar (
            id TEXT PRIMARY KEY,
            istasyon_id TEXT,
            cikis_numarasi TEXT NOT NULL,
            kapi_ismi TEXT NOT NULL,
            tuzlu_enlem REAL NOT NULL,
            tuzlu_boylam REAL NOT NULL,
            asansor_var_mi INTEGER DEFAULT 0,
            FOREIGN KEY (istasyon_id) REFERENCES istasyonlar (id)
        )
    ''')
    
    conn.commit()
    return conn, cursor

def test_verisi_ekle(conn, cursor):
    cursor.execute('''
        INSERT OR IGNORE INTO istasyonlar (id, isim, sehir) 
        VALUES ('m2_sisli', 'Şişli - Mecidiyeköy', 'İstanbul')
    ''')
    
    gercek_enlem = 41.0625
    gercek_boylam = 28.9922
    
    gizli_enlem = gercek_enlem + SALT_LAT
    gizli_boylam = gercek_boylam + SALT_LON
    
    cursor.execute('''
        INSERT OR REPLACE INTO kapilar (id, istasyon_id, cikis_numarasi, kapi_ismi, tuzlu_enlem, tuzlu_boylam, asansor_var_mi)
        VALUES ('m2_sisli_cikis_1', 'm2_sisli', '1', 'Şişli Camii Çıkışı', ?, ?, 1)
    ''', (gizli_enlem, gizli_boylam))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    baglanti, imlec = veritabani_olustur()
    test_verisi_ekle(baglanti, imlec)
    print("Tablolar güncel şema ile başarıyla oluşturuldu ve test verisi eklendi.")