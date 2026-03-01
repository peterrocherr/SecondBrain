import re, requests, io, os, uuid
from bs4 import BeautifulSoup
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import speech_recognition as sr
from pydub import AudioSegment

class ContentExtractor:
    
    @staticmethod
    def sanitize_text(text):
        if not text: return ""
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return re.sub(r'\s+', ' ', text).replace('"', "'").strip()

    @staticmethod
    def _obtener_datos(fuente):
        if fuente.startswith("http"):
            session = requests.Session()
            if "twilio.com" in fuente:
                session.auth = (os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
            
            r = session.get(fuente, timeout=20)
            r.raise_for_status()
            
            # Validar que no sea un error de Twilio en formato XML/HTML
            ctype = r.headers.get('Content-Type', '').lower()
            if "xml" in ctype or "html" in ctype:
                raise ValueError("Twilio devolvió un error en vez de multimedia.")
            
            return io.BytesIO(r.content)
        with open(fuente, "rb") as f: return io.BytesIO(f.read())

    @staticmethod
    def _transcribir(wav_io):
        rec = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = rec.record(source)
            return ContentExtractor.sanitize_text(rec.recognize_google(audio_data, language="es-ES"))

    @staticmethod
    def extraer_pdf(f):
        try:
            reader = PdfReader(ContentExtractor._obtener_datos(f))
            txt = " ".join([p.extract_text() for p in reader.pages[:5] if p.extract_text()])
            return f"\n[PDF]: {ContentExtractor.sanitize_text(txt)}"
        except Exception as e: return f"⚠️ ERROR PDF: {e}"

    @staticmethod
    def transcribir_audio(f):
        try:
            audio = AudioSegment.from_file(ContentExtractor._obtener_datos(f))
            w_io = io.BytesIO()
            audio.export(w_io, format="wav")
            w_io.seek(0)
            return f"\n[AUDIO]: {ContentExtractor._transcribir(w_io)}"
        except Exception as e: return f"⚠️ ERROR AUDIO: {e}"

    @staticmethod
    def extraer_video(f):
        tmp = f"tmp_{uuid.uuid4().hex}.mp4"
        try:
            with open(tmp, "wb") as t: t.write(ContentExtractor._obtener_datos(f).read())
            try:
                audio = AudioSegment.from_file(tmp)
            except Exception:
                # El vídeo no tiene pista de audio o no es decodificable
                return "⚠️ VIDEO_SIN_AUDIO"
            w_io = io.BytesIO()
            audio.export(w_io, format="wav")
            w_io.seek(0)
            return f"\n[VIDEO]: {ContentExtractor._transcribir(w_io)}"
        except Exception as e: return f"⚠️ ERROR VIDEO: {e}"
        finally: 
            if os.path.exists(tmp): os.remove(tmp)

    @staticmethod
    def extraer_web(url):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for s in soup(["script", "style"]): s.decompose()
            return f"\n[WEB]: {ContentExtractor.sanitize_text(soup.get_text())[:2000]}"
        except Exception as e: return f"⚠️ ERROR WEB: {e}"

    @staticmethod
    def extraer_youtube(url):
        try:
            v_id = re.search(r"(?:v=|\/)([\w-]{11})", url).group(1)
            t = YouTubeTranscriptApi.get_transcript(v_id, languages=['es', 'en'])
            return f"\n[YT]: {ContentExtractor.sanitize_text(' '.join([i['text'] for i in t]))}"
        except: return "⚠️ ERROR YT: Sin subtítulos."
    @staticmethod
    def extraer_imagen(fuente, llm):
        """Usa Gemini Vision para OCR y descripción inteligente de la imagen."""
        try:
            datos_imagen = ContentExtractor._obtener_datos(fuente).read()
            prompt = (
                "Actúa como un sistema de OCR avanzado. "
                "Extrae todo el texto visible en esta imagen con fidelidad exacta. "
                "Si no hay texto, describe brevemente qué muestra la imagen "
                "para guardarlo en un diario digital."
            )

            resultado = llm.analizar_imagen(datos_imagen, prompt)
            print(resultado)
            if resultado == "ERROR_LIMIT":
                return "⚠️ ERROR IMAGEN: límite de API alcanzado."
            return f"\n[IMAGE]: {ContentExtractor.sanitize_text(resultado)}"
        except Exception as e:
            return f"⚠️ ERROR IMAGEN: {e}"
