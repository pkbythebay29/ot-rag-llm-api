# Loader supporting PDF, image, audio, video
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import speech_recognition as sr
from moviepy.editor import AudioFileClip, VideoFileClip

SUPPORTED_TEXT = [".txt"]
SUPPORTED_PDF = [".pdf"]
SUPPORTED_IMG = [".jpg", ".jpeg", ".png"]
SUPPORTED_AUDIO = [".wav", ".flac"]
SUPPORTED_VIDEO = [".mp4"]

def load_docs(path: str) -> list[str]:
    ext = os.path.splitext(path)[-1].lower()

    if ext in SUPPORTED_TEXT:
        return _load_txt(path)
    elif ext in SUPPORTED_PDF:
        return _load_pdf(path)
    elif ext in SUPPORTED_IMG:
        return _load_image(path)
    elif ext in SUPPORTED_AUDIO:
        return _load_audio(path)
    elif ext in SUPPORTED_VIDEO:
        return _load_video(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _load_txt(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [f.read()]


def _load_pdf(path: str) -> list[str]:
    doc = fitz.open(path)
    return [page.get_text() for page in doc]


def _load_image(path: str) -> list[str]:
    img = Image.open(path)
    text = pytesseract.image_to_string(img)
    return [text]


def _load_audio(path: str) -> list[str]:
    recognizer = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = recognizer.record(source)
    try:
        return [recognizer.recognize_google(audio)]
    except sr.UnknownValueError:
        return ["[Unintelligible audio]"]


def _load_video(path: str) -> list[str]:
    temp_audio = "temp_audio.wav"
    clip = VideoFileClip(path)
    clip.audio.write_audiofile(temp_audio, logger=None)
    text = _load_audio(temp_audio)
    os.remove(temp_audio)
    return text
