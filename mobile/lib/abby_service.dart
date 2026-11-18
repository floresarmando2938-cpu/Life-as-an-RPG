import 'dart:convert';
import 'package:http/http.dart' as http;

class AbbyService {
  static const String serverUrl = "http://192.168.1.56:8000/comando";

  /// Envía la transcripción de voz al servidor central de Abby en tu PC
  static Future<String> sendCommand(String text) async {
    try {
      final response = await http.post(
        Uri.parse(serverUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"texto": text}),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        return data["respuesta"] ?? "Comando recibido con éxito.";
      } else {
        return "Error del servidor (${response.statusCode}): ${response.body}";
      }
    } catch (e) {
      return "No pude conectar con el servidor en 192.168.1.56:8000. Revisa que el PC y tu Moto G05 estén en la misma red Wi-Fi.";
    }
  }
}
