import re
import requests
import io
import os
import uuid
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
        text = re.sub(r'\s+', ' ', text)
        return text.replace('"', "'").replace('\\', '/').strip()

    @staticmethod
    def _obtener_flujo_datos(fuente):
        if fuente.startswith("http"):
            # --- LÓGICA DE SEGURIDAD PARA TWILIO ---
            if "twilio.com" in fuente:
                print("🔒 Detectada URL de Twilio. Aplicando credenciales de sesión...")
                twilio_sid = os.getenv("TWILIO_SID")
                twilio_token = os.getenv("TWILIO_TOKEN")
                
                # Session ayuda a mantener la auth si hay redirecciones internas a S3
                session = requests.Session()
                session.auth = (twilio_sid, twilio_token)
                response = session.get(fuente, timeout=20)
            else:
                response = requests.get(fuente, timeout=15)
                
            response.raise_for_status()

            # --- DEBUG Y DEFENSA ANTE ARCHIVOS FALSOS ---
            content_type = response.headers.get('Content-Type', '').lower()
            tamanio = len(response.content)
            print(f"📦 [DEBUG] Archivo bajado. Tipo: {content_type} | Tamaño: {tamanio} bytes")
            
            if "xml" in content_type or "html" in content_type:
                raise ValueError(f"Twilio denegó la descarga o envió texto (XML/HTML) en vez de multimedia.")

            return io.BytesIO(response.content)
        else:
            if not os.path.exists(fuente):
                raise FileNotFoundError(f"Archivo local no encontrado: {fuente}")
            with open(fuente, "rb") as f:
                return io.BytesIO(f.read())

    @staticmethod
    def _procesar_transcripcion(wav_io):
        """Método auxiliar interno para evitar repetir el código de SpeechRecognition."""
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            texto = recognizer.recognize_google(audio_data, language="es-ES")
        return ContentExtractor.sanitize_text(texto)

    @staticmethod
    def extraer_web(url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            for s in soup(["script", "style", "nav", "header", "footer", "aside"]): s.decompose()
            return f"\n[WEB CONTENT]: {ContentExtractor.sanitize_text(soup.get_text(separator=' '))[:2500]}"
        except Exception as e:
            return f"⚠️ ERROR WEB: {str(e)}"

    @staticmethod
    def extraer_youtube(url):
        try:
            regex = r"(?:v=|\/shorts\/|\/embed\/|\/v\/|youtu\.be\/|\/watch\?v=|\/watch\?.+&v=)([\w-]{11})"
            match = re.search(regex, url)
            if not match: return "⚠️ ERROR YT: No se reconoció el ID."
            
            transcript_list = YouTubeTranscriptApi.get_transcript(match.group(1), languages=['es', 'en'])
            texto = " ".join([t['text'] for t in transcript_list])
            return f"\n[YOUTUBE TRANSCRIPT]: {ContentExtractor.sanitize_text(texto)}"
        except:
            return "⚠️ ERROR YT: Vídeo sin subtítulos o fallo en la API."

    @staticmethod
    def extraer_pdf(fuente):
        try:
            f = ContentExtractor._obtener_flujo_datos(fuente)
            texto_pdf = " ".join([p.extract_text() for p in PdfReader(f).pages[:5] if p.extract_text()])
            if not texto_pdf.strip(): return "⚠️ ERROR PDF: Archivo sin texto."
            return f"\n[PDF CONTENT]: {ContentExtractor.sanitize_text(texto_pdf)}"
        except Exception as e:
            return f"⚠️ ERROR PDF: {str(e)}"

    @staticmethod
    def transcribir_audio(fuente):
        try:
            f = ContentExtractor._obtener_flujo_datos(fuente)
            audio = AudioSegment.from_file(f)
            
            if len(audio) == 0:
                return "\n[AUDIO TRANSCRIPT]: ⚠️ El archivo de audio está vacío."
                
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            texto = ContentExtractor._procesar_transcripcion(wav_io)
            return f"\n[AUDIO TRANSCRIPT]: {texto}"
            
        except IndexError:
            return "\n[AUDIO TRANSCRIPT]: ⚠️ ERROR: El archivo descargado está corrupto o no es un audio válido."
        except ValueError as ve:
            return f"\n[AUDIO TRANSCRIPT]: ⚠️ ERROR DESCARGA: {str(ve)}"
        except sr.UnknownValueError:
            return "\n[AUDIO TRANSCRIPT]: ⚠️ Audio ininteligible o sin voz detectada."
        except sr.RequestError as e:
            return f"\n[AUDIO TRANSCRIPT]: ⚠️ Error en el servicio de reconocimiento: {e}"
        except Exception as e:
            return f"⚠️ ERROR AUDIO: {str(e)}"

    @staticmethod
    def extraer_video(fuente):
        op_id = str(uuid.uuid4())[:8]
        temp_v = f"temp_v_{op_id}.mp4"
        
        try:
            datos = ContentExtractor._obtener_flujo_datos(fuente)
            with open(temp_v, "wb") as tmp:
                tmp.write(datos.read())

            audio = AudioSegment.from_file(temp_v)
            
            if len(audio) == 0:
                return "\n[VIDEO TRANSCRIPT]: ⚠️ El vídeo no contiene pista de audio."

            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_io.seek(0)

            texto = ContentExtractor._procesar_transcripcion(wav_io)
            return f"\n[VIDEO TRANSCRIPT]: {texto}"
            
        except IndexError:
            return "\n[VIDEO TRANSCRIPT]: ⚠️ ERROR: El archivo descargado está corrupto o no es un video válido."
        except ValueError as ve:
            return f"\n[VIDEO TRANSCRIPT]: ⚠️ ERROR DESCARGA: {str(ve)}"
        except sr.UnknownValueError:
            return "\n[VIDEO TRANSCRIPT]: ⚠️ No se pudo entender el audio del vídeo."
        except sr.RequestError as e:
            return f"\n[VIDEO TRANSCRIPT]: ⚠️ Error en el servicio de reconocimiento: {e}"
        except Exception as e:
            return f"⚠️ ERROR VÍDEO: {str(e)}"
        finally:
            if os.path.exists(temp_v): os.remove(temp_v)