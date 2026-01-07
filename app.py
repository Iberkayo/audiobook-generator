"""
🎧 Audiobook Generator - Streamlit App
EPUB/PDF → Profesyonel Sesli Kitap
"""
import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import streamlit as st
import asyncio
import tempfile
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List
from collections import Counter
from enum import Enum

import edge_tts
import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize

# ══════════════════════════════════════════════════════════════
# SAYFA AYARLARI
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="🎧 Audiobook Generator",
    page_icon="🎧",
    layout="wide"
)

# ══════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════
@dataclass
class Chapter:
    index: int
    title: str
    text: str
    @property
    def char_count(self):
        return len(self.text)

@dataclass
class BookData:
    title: str
    author: str
    chapters: List[Chapter]
    format: str
    @property
    def total_chars(self):
        return sum(c.char_count for c in self.chapters)

@dataclass
class Segment:
    id: int
    text: str
    pause_ms: int

class SegType(Enum):
    SENTENCE = 600
    PARAGRAPH = 1200
    DIALOGUE = 700
    CHAPTER = 3000

# ══════════════════════════════════════════════════════════════
# PARSER
# ══════════════════════════════════════════════════════════════
class SmartBookParser:
    def __init__(self):
        self.header_footer_lines = set()
        self.page_patterns = [r'^\s*\d+\s*$', r'^\s*-\s*\d+\s*-\s*$']

    def parse(self, file_path: str, file_ext: str) -> BookData:
        if file_ext == '.epub':
            return self.parse_epub(file_path)
        elif file_ext == '.pdf':
            return self.parse_pdf(file_path)
        else:
            raise ValueError(f"Desteklenmeyen format: {file_ext}")

    def parse_epub(self, file_path: str) -> BookData:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(file_path)

        title = book.get_metadata('DC', 'title')
        title = title[0][0] if title else "Bilinmeyen"
        author = book.get_metadata('DC', 'creator')
        author = author[0][0] if author else "Bilinmeyen"

        chapters = []
        idx = 1

        for spine_item in book.spine:
            item_id = spine_item[0]
            item = book.get_item_with_id(item_id)
            if item is None:
                continue

            soup = BeautifulSoup(item.get_content(), 'lxml')

            ch_title = ''
            for tag in ['h1', 'h2', 'h3']:
                h = soup.find(tag)
                if h:
                    ch_title = h.get_text().strip()
                    break

            for el in soup(['script', 'style', 'nav', 'header', 'footer']):
                el.decompose()

            text = soup.get_text(separator='\n')
            text = self._clean(text)

            if len(text.strip()) < 50:
                continue

            chapters.append(Chapter(idx, ch_title, text))
            idx += 1

        return BookData(title, author, chapters, 'epub')

    def parse_pdf(self, file_path: str) -> BookData:
        import pdfplumber

        title = Path(file_path).stem
        pages = []
        headers, footers = [], []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:20]:
                lines = self._lines(page)
                if lines:
                    headers.append(lines[0])
                    footers.append(lines[-1])

            self._detect_hf(headers, footers)

            for page in pdf.pages:
                t = self._extract_page(page)
                if t:
                    pages.append(t)

        raw = '\n\n'.join(pages)
        raw = self._deep_clean(raw)
        chapters = [Chapter(1, '', raw)]

        return BookData(title, "Bilinmeyen", chapters, 'pdf')

    def _lines(self, page):
        t = page.extract_text() or ''
        return [l.strip() for l in t.split('\n') if l.strip()]

    def _detect_hf(self, headers, footers):
        for l, c in Counter(headers).items():
            if c >= 3 and len(l) < 100:
                self.header_footer_lines.add(l.lower())
        for l, c in Counter(footers).items():
            if c >= 3 and len(l) < 100:
                self.header_footer_lines.add(l.lower())

    def _extract_page(self, page):
        t = page.extract_text(layout=True) or ''
        lines = []
        for l in t.split('\n'):
            s = l.strip()
            if not s:
                lines.append('')
                continue
            if s.lower() in self.header_footer_lines:
                continue
            if any(re.match(p, s) for p in self.page_patterns):
                continue
            lines.append(s)
        return '\n'.join(lines)

    def _clean(self, text):
        text = re.sub(r'[\t ]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return '\n'.join(l.strip() for l in text.split('\n')).strip()

    def _deep_clean(self, text):
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
        lines = text.split('\n')
        clean = []
        prev = ''
        for l in lines:
            s = l.strip()
            if not s:
                clean.append('')
                prev = ''
                continue
            if prev and (s == prev):
                continue
            clean.append(l)
            prev = s
        text = '\n'.join(clean)
        text = re.sub(r'(\w)-\n\s*(\w)', r'\1\2', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()

# ══════════════════════════════════════════════════════════════
# CONDUCTOR
# ══════════════════════════════════════════════════════════════
class Conductor:
    ABBR = ['Dr', 'Prof', 'vb', 'vs', 'bkz', 'örn']

    def __init__(self):
        esc = [re.escape(a) for a in self.ABBR]
        self.abbr_re = re.compile(r'\b(' + '|'.join(esc) + r')\.\s*', re.I)

    def split_sentences(self, text):
        prot = text
        phs = {}
        for i, m in enumerate(self.abbr_re.finditer(text)):
            ph = f'__A{i}__'
            phs[ph] = m.group(0)
            prot = prot.replace(m.group(0), ph, 1)

        sents = re.split(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜa-z])', prot)

        result = []
        for s in sents:
            for ph, orig in phs.items():
                s = s.replace(ph, orig)
            s = s.strip()
            if s and len(s) > 2:
                result.append(s)
        return result

    def is_dialogue(self, t):
        pats = [r'^[""]', r'^[—–-]\s', r'dedi[.!,]?$']
        return any(re.search(p, t, re.I) for p in pats)

    def process(self, chapters: List[Chapter]) -> List[Segment]:
        segs = []
        sid = 1

        for ch in chapters:
            if ch.title:
                segs.append(Segment(sid, ch.title, SegType.CHAPTER.value))
                sid += 1

            paras = [p.strip() for p in ch.text.split('\n\n') if p.strip()]
            for para in paras:
                sents = self.split_sentences(para)
                for i, sent in enumerate(sents):
                    is_last = (i == len(sents) - 1)
                    if self.is_dialogue(sent):
                        pause = SegType.DIALOGUE.value
                    elif is_last:
                        pause = SegType.PARAGRAPH.value
                    else:
                        pause = SegType.SENTENCE.value
                    segs.append(Segment(sid, sent, pause))
                    sid += 1

        return segs

# ══════════════════════════════════════════════════════════════
# TTS
# ══════════════════════════════════════════════════════════════
async def synthesize_segment(text: str, voice: str, path: str) -> bool:
    try:
        comm = edge_tts.Communicate(text, voice)
        await comm.save(path)
        return True
    except:
        return False

async def synthesize_all(segments: List[Segment], voice: str, temp_dir: str, progress_bar) -> List[str]:
    paths = []
    total = len(segments)
    
    for i, seg in enumerate(segments):
        p = os.path.join(temp_dir, f"seg_{seg.id:05d}.mp3")
        if await synthesize_segment(seg.text, voice, p):
            paths.append(p)
        progress_bar.progress((i + 1) / total, text=f"🎤 Sentezleniyor... {i+1}/{total}")
    
    return paths

# ══════════════════════════════════════════════════════════════
# STITCHER
# ══════════════════════════════════════════════════════════════
class Stitcher:
    def __init__(self, thresh=-50, xfade=15, room_db=-65):
        self.thresh = thresh
        self.xfade = xfade
        self.room_db = room_db

    def room_tone(self, ms, sr=24000):
        n = int(sr * ms / 1000)
        noise = (np.random.normal(0, 0.0005, n) * 32767).astype(np.int16)
        tone = AudioSegment(data=noise.tobytes(), sample_width=2, frame_rate=sr, channels=1)
        return tone + (self.room_db - tone.dBFS)

    def trim(self, a):
        start = 0
        for i in range(0, len(a), 10):
            if a[i:i+10].dBFS > self.thresh:
                start = max(0, i-20)
                break
        end = len(a)
        for i in range(len(a), 0, -10):
            if a[max(0,i-10):i].dBFS > self.thresh:
                end = min(len(a), i+20)
                break
        return a[start:end]

    def stitch(self, audios, pauses, progress_bar, use_room=True):
        if not audios:
            return AudioSegment.empty()
        
        out = self.trim(audios[0])
        total = len(audios)
        
        for i, a in enumerate(audios[1:], 1):
            t = self.trim(a)
            p_ms = pauses[i-1] if i-1 < len(pauses) else 600
            p = self.room_tone(p_ms) if use_room else AudioSegment.silent(p_ms)
            try:
                out = out.append(p, crossfade=min(self.xfade, len(p)//2))
                out = out.append(t, crossfade=min(self.xfade, len(t)//2))
            except:
                out = out + p + t
            
            progress_bar.progress(i / total, text=f"🧵 Birleştiriliyor... {i}/{total}")
        
        return normalize(out)

# ══════════════════════════════════════════════════════════════
# STREAMLIT UI
# ══════════════════════════════════════════════════════════════
def main():
    st.title("🎧 Audiobook Generator")
    st.markdown("**EPUB/PDF → Profesyonel Sesli Kitap**")
    
    # Sidebar - Ayarlar
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        
        voice_option = st.selectbox(
            "🎤 Ses",
            ["Erkek (Ahmet)", "Kadın (Emel)"],
            index=0
        )
        voice = "tr-TR-AhmetNeural" if "Erkek" in voice_option else "tr-TR-EmelNeural"
        
        use_room_tone = st.checkbox("🔇 Room Tone", value=True, help="Doğal arka plan sesi")
        
        st.divider()
        st.markdown("### 📊 Nasıl Çalışır?")
        st.markdown("""
        1. EPUB/PDF yükle
        2. Bölüm seç
        3. "Oluştur" tıkla
        4. MP3 indir
        """)
    
    # Ana alan
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📁 Dosya Yükle")
        uploaded_file = st.file_uploader(
            "EPUB veya PDF seçin",
            type=['epub', 'pdf'],
            help="Maksimum 200MB"
        )
    
    # Dosya yüklendiyse
    if uploaded_file:
        file_ext = Path(uploaded_file.name).suffix.lower()
        
        # Geçici dosyaya kaydet
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Parse et
        with st.spinner("📖 Kitap okunuyor..."):
            parser = SmartBookParser()
            try:
                book = parser.parse(tmp_path, file_ext)
                st.session_state['book'] = book
                st.session_state['tmp_path'] = tmp_path
            except Exception as e:
                st.error(f"❌ Parse hatası: {e}")
                return
        
        with col2:
            st.header("📚 Kitap Bilgileri")
            st.markdown(f"**📖 {book.title}**")
            st.markdown(f"**✍️ {book.author}**")
            st.markdown(f"**📑 {len(book.chapters)} bölüm**")
            st.markdown(f"**🔤 {book.total_chars:,} karakter**")
        
        st.divider()
        
        # Bölüm seçimi
        st.header("📑 Bölüm Seçimi")
        
        chapter_options = [f"[{ch.index}] {ch.title or '(Başlıksız)'}" for ch in book.chapters]
        
        col_a, col_b = st.columns(2)
        with col_a:
            start_ch = st.selectbox("Başlangıç", chapter_options, index=0)
        with col_b:
            end_ch = st.selectbox("Bitiş", chapter_options, index=0)
        
        start_idx = chapter_options.index(start_ch) + 1
        end_idx = chapter_options.index(end_ch) + 1
        
        if start_idx > end_idx:
            st.warning("⚠️ Başlangıç bölümü bitiş bölümünden büyük olamaz!")
            return
        
        selected_chapters = [ch for ch in book.chapters if start_idx <= ch.index <= end_idx]
        
        # Önizleme
        with st.expander("👀 Metin Önizleme"):
            if selected_chapters:
                ch = selected_chapters[0]
                st.markdown(f"**Bölüm {ch.index}: {ch.title or '(Başlıksız)'}**")
                st.text(ch.text[:1000] + "..." if len(ch.text) > 1000 else ch.text)
        
        st.divider()
        
        # Oluştur butonu
        if st.button("🚀 Audiobook Oluştur", type="primary", use_container_width=True):
            
            # Progress container
            progress_container = st.container()
            
            with progress_container:
                # Adım 1: Segmentasyon
                st.markdown("### 🎼 Adım 1: Segmentasyon")
                conductor = Conductor()
                segments = conductor.process(selected_chapters)
                st.success(f"✅ {len(segments)} segment oluşturuldu")
                
                # Adım 2: TTS
                st.markdown("### 🎤 Adım 2: Ses Sentezi")
                tts_progress = st.progress(0, text="Başlıyor...")
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Async çalıştır
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    paths = loop.run_until_complete(
                        synthesize_all(segments, voice, temp_dir, tts_progress)
                    )
                    loop.close()
                    
                    st.success(f"✅ {len(paths)} ses dosyası oluşturuldu")
                    
                    # Adım 3: Birleştirme
                    st.markdown("### 🧵 Adım 3: Birleştirme")
                    stitch_progress = st.progress(0, text="Başlıyor...")
                    
                    audios = [AudioSegment.from_mp3(p) for p in paths]
                    pauses = [s.pause_ms for s in segments]
                    
                    stitcher = Stitcher()
                    combined = stitcher.stitch(audios, pauses, stitch_progress, use_room_tone)
                    
                    st.success("✅ Birleştirme tamamlandı")
                    
                    # MP3 oluştur
                    st.markdown("### 🎧 Sonuç")
                    
                    output_path = os.path.join(temp_dir, "audiobook.mp3")
                    combined.export(output_path, format="mp3", bitrate="192k")
                    
                    duration = len(combined) / 1000
                    mins = int(duration // 60)
                    secs = int(duration % 60)
                    
                    st.markdown(f"**⏱️ Süre:** {mins}:{secs:02d}")
                    
                    # Audio player
                    with open(output_path, "rb") as f:
                        audio_bytes = f.read()
                    
                    st.audio(audio_bytes, format="audio/mp3")
                    
                    # İndirme butonu
                    safe_name = re.sub(r'[^\w\s-]', '', book.title)[:30].replace(' ', '_')
                    st.download_button(
                        label="📥 MP3 İndir",
                        data=audio_bytes,
                        file_name=f"{safe_name}_audiobook.mp3",
                        mime="audio/mpeg",
                        use_container_width=True
                    )

if __name__ == "__main__":
    main()
