(function () {
  const Voice = {
    recognition: null,
    isListening: false,
    isMuted: false,

    init() {
      const micButton = document.getElementById('voice-button');
      if (!micButton) return;

      const RecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!RecognitionClass) {
        micButton.hidden = true;
        micButton.style.display = 'none';
        return;
      }

      // This works best in Chrome/Edge. If SpeechRecognition is not supported, the mic is hidden and the app falls back to text-only.
      const recognition = new RecognitionClass();
      recognition.lang = 'en-IN';
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        this.isListening = true;
        micButton.classList.add('listening');
        micButton.setAttribute('aria-label', 'Listening');
      };

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join(' ')
          .trim();

        if (transcript && typeof window.orcaApp?.handleVoiceTranscript === 'function') {
          window.orcaApp.handleVoiceTranscript(transcript);
        }
      };

      recognition.onerror = () => {
        this.isListening = false;
        micButton.classList.remove('listening');
        micButton.setAttribute('aria-label', 'Voice input');
      };

      recognition.onend = () => {
        this.isListening = false;
        micButton.classList.remove('listening');
        micButton.setAttribute('aria-label', 'Voice input');
      };

      this.recognition = recognition;

      micButton.addEventListener('click', () => {
        if (this.isListening) {
          this.recognition.stop();
          return;
        }
        try {
          this.recognition.start();
        } catch (error) {
          console.warn('Speech recognition already active or unavailable:', error);
        }
      });
    },

    toggleMute() {
      this.isMuted = !this.isMuted;
      const muteButton = document.getElementById('voice-mute-button');
      if (muteButton) {
        muteButton.textContent = this.isMuted ? '🔇' : '🔊';
      }
      if (this.isMuted) {
        window.speechSynthesis?.cancel();
      }
    },

    speak(text) {
      if (this.isMuted || !text || !('speechSynthesis' in window)) return;
      const cleanText = String(text).trim();
      if (!cleanText) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1;
      utterance.pitch = 1;
      utterance.lang = 'en-IN';
      window.speechSynthesis.speak(utterance);
    },

    announceLoading() {
      this.speak('Checking conditions.');
    }
  };

  window.voice = Voice;
  document.addEventListener('DOMContentLoaded', () => Voice.init());
})();
