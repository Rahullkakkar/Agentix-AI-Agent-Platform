import whisper
import sounddevice as sd
import numpy as np
import edge_tts
import asyncio
import tempfile
import os
import soundfile as sf
from engine.voice import VoiceSession


class LocalVoiceSession:
    def __init__(self):
        # Whisper tiny — fast, accurate enough for phone-quality short utterances
        self.model = whisper.load_model("tiny")

        # ✅ Voice selection — change to switch accent/gender
        # Full list: run `edge-tts --list-voices | grep en-` in terminal
        self.voice = "en-IN-NeerjaExpressiveNeural"  # Indian English female
        # self.voice = "en-IN-PrabhatNeural"  # Indian English male
        # self.voice = "en-US-JennyNeural"    # US English female
        # self.voice = "en-US-GuyNeural"      # US English male
        # self.voice = "en-GB-SoniaNeural"    # British English female
        # self.voice = "en-GB-RyanNeural"     # British English male

        self._is_speaking = False           # 🔇 mic gate flag

    # ---------------- SPEAK ----------------
    def speak(self, text: str):
        if not text:
            return
        print(f"AGENT: {text}")
        self._is_speaking = True            # 🔇 gate mic BEFORE speaking starts
        try:
            asyncio.run(self._speak_async(text))
        finally:
            self._is_speaking = False       # 🎙 reopen mic after speech ends

    async def _speak_async(self, text: str):
        communicate = edge_tts.Communicate(text, self.voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        try:
            await communicate.save(tmp_path)
            data, samplerate = sf.read(tmp_path)
            sd.play(data, samplerate)
            sd.wait()
        finally:
            os.unlink(tmp_path)

    # ---------------- LISTEN ----------------
    def listen(self, max_duration=8, samplerate=16000, silence_threshold=0.01, silence_seconds=1.2) -> str:
        """
        VAD-based listening — stops as soon as user stops talking
        instead of always waiting the full fixed duration.
        """
        # 🔇 Don't start listening until TTS is fully done
        while self._is_speaking:
            pass

        print("🎙 Listening...")

        chunk_size = int(samplerate * 0.1)  # 100ms chunks
        max_chunks = int(max_duration * samplerate / chunk_size)
        silence_chunks_needed = int(silence_seconds / 0.1)

        recorded = []
        silence_count = 0
        started_speaking = False

        with sd.InputStream(samplerate=samplerate, channels=1, dtype="float32") as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(chunk_size)
                chunk = chunk.flatten()
                rms = np.sqrt(np.mean(chunk ** 2))

                recorded.append(chunk)

                if rms > silence_threshold:
                    started_speaking = True
                    silence_count = 0
                elif started_speaking:
                    silence_count += 1
                    if silence_count >= silence_chunks_needed:
                        break  # user stopped talking

        audio = np.concatenate(recorded)
        result = self.model.transcribe(audio, fp16=False, language="en")
        text = result["text"].strip()
        print(f"USER: {text}")
        return text
