class VoiceSession:
    def speak(self, text: str):
        raise NotImplementedError

    def listen(self) -> str:
        raise NotImplementedError

    def hangup(self):
        pass