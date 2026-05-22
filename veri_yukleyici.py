import sqlite3
import pandas as pd

# Tuz anahtarları
SALT_LAT = 0.0050
SALT_LON = -0.0030

def veritabanini_hazirla():
    """Yeni sütunlara uygun olarak veritabanı şemasını yeniler."""
    conn = sqlite3.connect("smartexit.db")
    cursor = conn.cursor()
    
    # İstasyonlar tablosunu koruyalım (yoksa oluşturalım)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS istasyonlar (
            id TEXT PRIMARY KEY,
            isim TEXT NOT NULL,
            sehir TEXT NOT NULL
        )
    ''')
    
    # DİKKAT: Eski kapilar tablosunu silip YENİ sütunlarla tekrar oluşturuyoruz
    cursor.execute('DROP TABLE IF EXISTS kapilar')
    cursor.execute('''
        CREATE TABLE kapilar (
            id TEXT PRIMARY KEY,
            istasyon_id TEXT,
            cikis_numarasi TEXT NOT NULL,  -- YENİ EKLENEN SÜTUN!      
            tuzlu_enlem REAL NOT NULL,
            tuzlu_boylam REAL NOT NULL,
            kapi_ismi TEXT, 
            asansor_var_mi INTEGER DEFAULT 0,
            FOREIGN KEY (istasyon_id) REFERENCES istasyonlar (id)
        )
    ''')
    conn.commit()
    return conn, cursor

def csv_verilerini_yukle(csv_dosya_yolu):
    print(f"{csv_dosya_yolu} dosyası okunuyor...")
    df = pd.read_csv(csv_dosya_yolu)
    
    # Koordinatları tuzluyoruz
    df['tuzlu_enlem'] = df['gercek_enlem'] + SALT_LAT
    df['tuzlu_boylam'] = df['gercek_boylam'] + SALT_LON
    
    # Veritabanını yeni yapıya geçir
    conn, cursor = veritabanini_hazirla()
    
    # EKSTRA ZEKİ ÖZELLİK: CSV'de gördüğü istasyonları DB'de yoksa otomatik ekler
    benzersiz_istasyonlar = df['istasyon_id'].unique()
    for istasyon in benzersiz_istasyonlar:
        cursor.execute('INSERT OR IGNORE INTO istasyonlar (id, isim, sehir) VALUES (?, ?, ?)', (istasyon, istasyon, 'İstanbul'))

    # Kapıları veritabanına yaz
    eklenen_kayit = 0
    for index, row in df.iterrows():
        # Benzersiz ID'yi artık çıkış numarası ile üretiyoruz (Örn: m2_sisli_cikis_1)
        benzersiz_id = f"{row['istasyon_id']}_cikis_{row['cikis_numarasi']}"
        
        try:
            cursor.execute('''
                INSERT INTO kapilar (id, istasyon_id, cikis_numarasi, kapi_ismi, tuzlu_enlem, tuzlu_boylam, asansor_var_mi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                benzersiz_id, 
                row['istasyon_id'], 
                str(row['cikis_numarasi']), # Metne çevirdik ki 1A, 2B gibi numaralar da girilebilsin
                row['kapi_ismi'], 
                row['tuzlu_enlem'], 
                row['tuzlu_boylam'], 
                row['asansor_var_mi']
            ))
            eklenen_kayit += 1
        except Exception as e:
            print(f"Hata: {row['kapi_ismi']} eklenemedi! Detay: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"Başarılı! Toplam {eklenen_kayit} kapı, yeni 'Çıkış Numarası' sistemiyle veritabanına eklendi.")

if __name__ == "__main__":
    csv_verilerini_yukle("kapilar.csv")
