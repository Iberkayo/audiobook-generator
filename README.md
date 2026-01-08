# 🎧 Audiobook Generator

**EPUB/PDF → Profesyonel Sesli Kitap**

Yapay zeka tabanlı metin-konuşma teknolojisi ile kitaplarınızı doğal Türkçe sesli kitaba dönüştürün.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/KULLANICI_ADIN/audiobook-generator/blob/main/colab_audiobook_v9.ipynb)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://KULLANICI-audiobook.streamlit.app)

---

## 🎯 Problem

İlk denemede metni direkt TTS'e verdim. Sonuç: **Robotik, kopuk, dinlenemez.**

**Neden?** TTS motorları her chunk'ta "state reset" yapıyor:
- Chunk A bitiyor → tonlama düşüyor
- Chunk B başlıyor → yüksek perdeden giriyor  
- **Sonuç:** Prozodik uyumsuzluk = "takılma" hissi

---

## 🏗️ Mimari Çözüm: Şef-Terzi Modeli

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   📁 EPUB/PDF                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ 📖 AKILLI PARSER                                        │  │
│   │ • EPUB: Spine sıralı okuma (doğru bölüm sırası)        │  │
│   │ • PDF: Header/footer tespiti & temizleme               │  │
│   │ • Duplicate satır eliminasyonu                          │  │
│   │ • Tireleme düzeltme (sa-\ntır → satır)                 │  │
│   └─────────────────────────────────────────────────────────┘  │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ 🎼 ŞEF (Conductor)                                      │  │
│   │ • Türkçe cümle sınır tespiti (kısaltma korumalı)       │  │
│   │ • Diyalog tespiti (regex pattern matching)             │  │
│   │ • Akıllı Pause Map:                                     │  │
│   │   - Cümle sonu: 600ms                                   │  │
│   │   - Paragraf sonu: 1200ms                               │  │
│   │   - Diyalog: 700ms                                      │  │
│   │   - Bölüm geçişi: 3000ms                               │  │
│   └─────────────────────────────────────────────────────────┘  │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ 🎤 TTS ENGINE                                           │  │
│   │ • Her cümle = Ayrı ses dosyası                         │  │
│   │ • Edge TTS Neural (tr-TR-AhmetNeural/EmelNeural)       │  │
│   │ • Async batch processing                                │  │
│   └─────────────────────────────────────────────────────────┘  │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ 🧵 TERZİ (Stitcher)                                     │  │
│   │ • Silence trimming (VAD tabanlı, -50dB threshold)      │  │
│   │ • Room tone injection (-65dB Gaussian noise)           │  │
│   │ • Crossfade (15ms, click/pop önleme)                   │  │
│   │ • RMS normalization                                     │  │
│   └─────────────────────────────────────────────────────────┘  │
│        │                                                        │
│        ▼                                                        │
│   🎧 MP3 AUDIOBOOK                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Teknik Detaylar

### 1️⃣ Türkçe Cümle Sınır Tespiti (SBD)

**Problem:** `"Dr. Ahmet geldi."` → Yanlış: `["Dr.", "Ahmet geldi."]`

**Çözüm:** Kısaltma regex + placeholder sistemi

```python
ABBREVIATIONS = ['Dr', 'Prof', 'vb', 'vs', 'bkz', 'örn', 'M.Ö', 'M.S']
# Placeholder ile koruma → split → geri yükleme
```

### 2️⃣ EPUB Spine Sıralaması

**Problem:** `get_items()` rastgele sıra döndürüyor

**Çözüm:** `book.spine` ile doğru okuma sırası

```python
for spine_item in book.spine:
    item_id = spine_item[0]
    item = book.get_item_with_id(item_id)
```

### 3️⃣ PDF Header/Footer Tespiti

```python
# İlk 20 sayfada tekrar eden satırları bul
for page in pdf.pages[:20]:
    headers.append(lines[0])
    footers.append(lines[-1])

# 3+ kez tekrar eden = header/footer
header_footer_lines = {l for l, c in Counter(headers).items() if c >= 3}
```

### 4️⃣ Room Tone vs Mutlak Sessizlik

**Problem:** Mutlak sessizlik (0 amplitude) kulaklıkta "vakum" etkisi yaratıyor

**Çözüm:** -65dB Gaussian noise injection

```python
def room_tone(self, duration_ms):
    noise = np.random.normal(0, 0.0005, samples)
    # -65dB seviyesinde doğal "oda sesi"
```

### 5️⃣ Crossfade ile Click Önleme

**Problem:** İki ses birleşirken waveform uyumsuzluğu → "pop" sesi

**Çözüm:** 15ms crossfade

```python
combined.append(audio, crossfade=15)
```

---

## 📊 Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| **Frontend** | Streamlit |
| **TTS** | Edge TTS (Neural Turkish) |
| **PDF Parser** | pdfplumber |
| **EPUB Parser** | ebooklib, BeautifulSoup |
| **Audio Processing** | pydub, numpy |

---

## 🚀 Kullanım

### Google Colab (Önerilen)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/KULLANICI_ADIN/audiobook-generator/blob/main/colab_audiobook_v9.ipynb)

### Lokal Kurulum

```bash
# Klonla
git clone https://github.com/KULLANICI_ADIN/audiobook-generator.git
cd audiobook-generator

# Bağımlılıkları yükle
pip install -r requirements.txt

# Streamlit app'i çalıştır
streamlit run app.py
```

---

## 📁 Proje Yapısı

```
audiobook-generator/
├── app.py                      # Streamlit web uygulaması
├── colab_audiobook_v9.ipynb    # Google Colab notebook
├── requirements.txt            # Python bağımlılıkları
├── packages.txt                # Sistem bağımlılıkları
└── README.md                   # Bu dosya
```

---

## 🎯 Öğrenilen Dersler

1. **Sesli kitap üretimi ≠ TTS çağrısı** - Prozodi, duraklama, segment geçişleri kritik
2. **PDF "garbage in, garbage out"** - Akıllı metin çıkarma şart
3. **Mutlak sessizlik rahatsız edici** - Room tone injection gerekli
4. **State reset problemi** - Her cümle ayrı, sonra birleştir

---

## 📝 Lisans

MIT

---

## 🤝 Katkıda Bulunun

Pull request'ler memnuniyetle karşılanır!

---

**⭐ Beğendiyseniz yıldız vermeyi unutmayın!**
