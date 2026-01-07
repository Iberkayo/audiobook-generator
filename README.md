# 🎧 Audiobook Generator

EPUB/PDF dosyalarını profesyonel sesli kitaba dönüştürün.

## 🚀 Özellikler

- 📗 **EPUB Desteği** - Spine sıralı, temiz metin
- 📕 **Akıllı PDF Parser** - Header/footer temizleme
- 🎼 **Şef Modülü** - Cümle bazlı segmentasyon
- 🎤 **Edge TTS** - Doğal Türkçe ses
- 🧵 **Terzi Modülü** - Crossfade + Room Tone

## 📦 Kurulum

```bash
pip install -r requirements.txt
```

## ▶️ Çalıştırma

```bash
streamlit run app.py
```

## 🌐 Deploy Seçenekleri

### 1. Streamlit Cloud (ÜCRETSİZ - ÖNERİLEN)

1. GitHub'a repo oluştur
2. Bu dosyaları yükle
3. [share.streamlit.io](https://share.streamlit.io) git
4. "New app" → GitHub reposunu seç
5. Deploy!

### 2. Hugging Face Spaces (ÜCRETSİZ)

1. [huggingface.co/spaces](https://huggingface.co/spaces) git
2. "Create new Space" → Streamlit seç
3. Dosyaları yükle
4. Otomatik deploy!

### 3. Railway (Aylık $5)

```bash
railway login
railway init
railway up
```

## 📁 Dosya Yapısı

```
audiobook_app/
├── app.py              # Ana uygulama
├── requirements.txt    # Bağımlılıklar
└── README.md          # Bu dosya
```

## 🎯 Kullanım

1. EPUB veya PDF yükle
2. Bölüm seç (başlangıç-bitiş)
3. Ses seç (Erkek/Kadın)
4. "Oluştur" tıkla
5. MP3 indir!

## 📝 Lisans

MIT
