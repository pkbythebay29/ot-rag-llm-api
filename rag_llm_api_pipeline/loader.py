# Loader supporting PDF, image, audio, video
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import speech_recognition as sr
from moviepy.editor import VideoFileClip

SUPPORTED_TEXT = [".txt"]
SUPPORTED_PDF = [".pdf"]
SUPPORTED_IMG = [".jpg", ".jpeg", ".png"]
SUPPORTED_AUDIO = [".wav", ".flac"]
SUPPORTED_VIDEO = [".mp4"]


def load_docs(path: str, ocr_lang: str = "eng") -> list[str]:
    path = os.path.abspath(path)
    ext = os.path.splitext(path)[-1].lower()

    if ext in SUPPORTED_TEXT:
        return _load_txt(path)
    elif ext in SUPPORTED_PDF:
        return _load_pdf(path)
    elif ext in SUPPORTED_IMG:
        return _load_image(path, ocr_lang)
    elif ext in SUPPORTED_AUDIO:
        return _load_audio(path)
    elif ext in SUPPORTED_VIDEO:
        return _load_video(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _load_txt(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [f.read()]
    except Exception as e:
        print(f"Error reading text file {path}: {e}")
        return []


def _load_pdf(path: str) -> list[str]:
    try:
        doc = fitz.open(path)
        return [page.get_text() for page in doc]
    except Exception as e:
        print(f"Error reading PDF {path}: {e}")
        return []


def _load_image(path: str, lang: str) -> list[str]:
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang=lang)
        return [text]
    except Exception as e:
        print(f"Error reading image {path}: {e}")
        return []


def _load_audio(path: str) -> list[str]:
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(path) as source:
            audio = recognizer.record(source)
        return [recognizer.recognize_google(audio)]
    except sr.UnknownValueError:
        return ["[Unintelligible audio]"]
    except Exception as e:
        print(f"Error reading audio {path}: {e}")
        return []


def _load_video(path: str) -> list[str]:
    temp_audio = "temp_audio.wav"
    try:
        clip = VideoFileClip(path)
        clip.audio.write_audiofile(temp_audio, logger=None)
        text = _load_audio(temp_audio)
    except Exception as e:
        print(f"Error extracting audio from video {path}: {e}")
        text = []
    finally:
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
    return text
