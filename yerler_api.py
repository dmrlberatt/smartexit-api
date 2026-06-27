"""
yerler_api.py — Kullanıcıların Maps'ten getirdiği koordinatları saklar.
api.py'ye şunu ekle:
    from yerler_api import router as yerler_router
    app.include_router(yerler_router)
"""
from urllib.parse import urlparse, parse_qs
from fastapi import APIRouter
from pydantic import BaseModel
import sqlite3
import os
import requests as req
import re

router = APIRouter()
DB_PATH = os.path.join(os.path.dirname(__file__), "smartexit.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def tablo_olustur():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS yerler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            acik_adres TEXT DEFAULT '',
            enlem REAL NOT NULL,
            boylam REAL NOT NULL,
            arama_sayisi INTEGER DEFAULT 1,
            olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_yerler_ad ON yerler(ad)
    """)
    conn.commit()
    conn.close()


# Uygulama başlarken tabloyu oluştur
tablo_olustur()


class YerKaydetRequest(BaseModel):
    ad: str
    enlem: float
    boylam: float
    acik_adres: str = ""


@router.post("/api/v1/yerler/kaydet")
def yer_kaydet(request: YerKaydetRequest):
    """
    Maps'ten gelen koordinatı kaydet.
    Aynı ad varsa arama_sayisi'ni artır.
    """
    if not request.ad or not request.ad.strip():
        return {"durum": "hata", "mesaj": "Ad boş olamaz"}

    ad = request.ad.strip()

    conn = get_db()
    try:
        # Aynı ad ve yakın koordinat var mı?
        mevcut = conn.execute("""
            SELECT id, arama_sayisi FROM yerler
            WHERE ad = ?
            AND ABS(enlem - ?) < 0.001
            AND ABS(boylam - ?) < 0.001
            LIMIT 1
        """, (ad, request.enlem, request.boylam)).fetchone()

        if mevcut:
            # Varsa arama sayısını artır
            conn.execute("""
                UPDATE yerler SET arama_sayisi = arama_sayisi + 1
                WHERE id = ?
            """, (mevcut["id"],))
        else:
            # Yoksa yeni kayıt ekle
            conn.execute("""
                INSERT INTO yerler (ad, acik_adres, enlem, boylam)
                VALUES (?, ?, ?, ?)
            """, (ad, request.acik_adres, request.enlem, request.boylam))

        conn.commit()
        return {"durum": "basarili"}
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
    finally:
        conn.close()


@router.get("/api/v1/yerler/ara")
def yer_ara(q: str):
    """
    Kendi DB'den yer ara. Arama sayısına göre sıralar.
    Kullanıcı bir yeri ne kadar çok getirdiyse o kadar üste çıkar.
    """
    if not q or len(q) < 2:
        return []

    conn = get_db()
    try:
        q_lower = q.lower()
        sonuclar = conn.execute("""
            SELECT ad, acik_adres, enlem, boylam, arama_sayisi
            FROM yerler
            WHERE LOWER(ad) LIKE ?
            ORDER BY arama_sayisi DESC, ad ASC
            LIMIT 5
        """, (f"%{q_lower}%",)).fetchall()

        return [
            {
                "ad": r["ad"],
                "acik_adres": r["acik_adres"],
                "enlem": r["enlem"],
                "boylam": r["boylam"],
            }
            for r in sonuclar
        ]
    except Exception as e:
        return []
    finally:
        conn.close()


@router.get("/api/v1/yerler/populer")
def populer_yerler():
    """
    En çok aranan 20 yeri döndürür.
    İstatistik ve veri kalitesi için kullanılabilir.
    """
    conn = get_db()
    try:
        sonuclar = conn.execute("""
            SELECT ad, acik_adres, enlem, boylam, arama_sayisi
            FROM yerler
            ORDER BY arama_sayisi DESC
            LIMIT 20
        """).fetchall()

        return [dict(r) for r in sonuclar]
    finally:
        conn.close()

@router.get("/api/v1/maps-link-coz")
def maps_link_coz(link: str):
    try:
        # 1. Adım: Sadece HEAD isteği atarak yönlendirmeleri al (Daha az RAM harcar)
        # Bazen full GET isteği gereksiz yük bindirir.
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        # Linki olduğu gibi regex ile kontrol et (Bazı linkler yönlendirme gerektirmez)
        # Önce linkin kendisini tara
        def extract_coords(url_string):
            # Format: @41.0082,28.9784
            match1 = re.search(r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', url_string)
            if match1: return match1.groups()
            
            # Format: !3d41.0082!4d28.9784 (Google Share linkleri)
            match2 = re.search(r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)', url_string)
            if match2: return match2.groups()
            
            # Format: q=41.008,28.978
            match3 = re.search(r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)', url_string)
            if match3: return match3.groups()
            
            return None

        # Linki doğrudan tara
        coords = extract_coords(link)
        if coords:
            return {"durum": "basarili", "enlem": float(coords[0]), "boylam": float(coords[1])}

        # 2. Adım: Eğer linkte yoksa, yönlendirme sonrası URL'yi al
        response = req.head(link, headers=headers, allow_redirects=True, timeout=10)
        final_url = response.url
        
        coords = extract_coords(final_url)
        if coords:
            return {"durum": "basarili", "enlem": float(coords[0]), "boylam": float(coords[1])}

        return {"durum": "bulunamadi", "url": final_url}

    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}
