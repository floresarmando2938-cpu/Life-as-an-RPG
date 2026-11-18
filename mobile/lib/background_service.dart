import 'dart:async';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'abby_service.dart';

// Callback obligatorio para flutter_foreground_task en Android
@pragma('vm:entry-point')
void startCallback() {
  FlutterForegroundTask.setTaskHandler(AbbyWakeWordTaskHandler());
}

class AbbyWakeWordTaskHandler extends TaskHandler {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();
  bool _isListening = false;

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    await _initTts();
    await _startContinuousListen();
  }

  Future<void> _initTts() async {
    await _tts.setLanguage("es-MX");
    await _tts.setSpeechRate(0.9);
    await _tts.setVolume(1.0);
  }

  Future<void> _startContinuousListen() async {
    bool available = await _speech.initialize(
      onError: (val) => _retryListening(),
      onStatus: (val) {
        if (val == 'done' || val == 'notListening') {
          _retryListening();
        }
      },
    );

    if (available) {
      _listenForWakeWord();
    }
  }

  void _listenForWakeWord() {
    if (_isListening) return;
    _isListening = true;

    _speech.listen(
      localeId: 'es_MX',
      listenMode: stt.ListenMode.dictation,
      partialResults: true,
      onResult: (val) async {
        String recognized = val.recognizedWords.toLowerCase();
        // Detección de la palabra clave: 'abby' u 'oye abby'
        if (recognized.contains('abby') || recognized.contains('api') || recognized.contains('avi')) {
          _speech.stop();
          _isListening = false;

          // Extraer la orden posterior o pedir comando
          String command = recognized.replaceAll(RegExp(r'(oye\s+)?abby'), '').trim();
          if (command.isEmpty) {
            await _tts.speak("¿Sí? Dime.");
          } else {
            // Notificar y enviar al servidor
            String reply = await AbbyService.sendCommand(command);
            FlutterForegroundTask.updateService(
              notificationTitle: 'Abby respondió',
              notificationText: reply,
            );
            await _tts.speak(reply);
          }
          // Reiniciar escucha pasiva
          Future.delayed(const Duration(seconds: 1), () => _retryListening());
        }
      },
    );
  }

  void _retryListening() {
    _isListening = false;
    Future.delayed(const Duration(milliseconds: 500), () {
      if (!_isListening) {
        _listenForWakeWord();
      }
    });
  }

  @override
  Future<void> onRepeatEvent(DateTime timestamp) async {
    // Mantener vivo el ciclo de escucha
    if (!_speech.isListening && !_isListening) {
      _listenForWakeWord();
    }
  }

  @override
  Future<void> onDestroy(DateTime timestamp) async {
    await _speech.stop();
    await _tts.stop();
  }
}
