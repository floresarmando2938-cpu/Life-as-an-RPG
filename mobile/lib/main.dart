import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:permission_handler/permission_handler.dart';

import 'abby_service.dart';
import 'background_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Inicializar Supabase en móvil con variables configurables
  const supabaseUrl = String.fromEnvironment('SUPABASE_URL', defaultValue: 'https://mynmldhqiflptjmhsuoq.supabase.co');
  const supabaseKey = String.fromEnvironment('SUPABASE_KEY', defaultValue: 'YOUR_SUPABASE_ANON_KEY');

  await Supabase.initialize(
    url: supabaseUrl,
    anonKey: supabaseKey,
  );

  runApp(const AbbyApp());
}

class AbbyApp extends StatelessWidget {
  const AbbyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Abby RPG',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F111A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6C5CE7),
          secondary: Color(0xFF00CEC9),
          surface: Color(0xFF1E2130),
        ),
      ),
      home: const AbbyHomeScreen(),
    );
  }
}

class AbbyHomeScreen extends StatefulWidget {
  const AbbyHomeScreen({super.key});

  @override
  State<AbbyHomeScreen> createState() => _AbbyHomeScreenState();
}

class _AbbyHomeScreenState extends State<AbbyHomeScreen> {
  final supabase = Supabase.instance.client;
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();

  // Estado RPG
  int level = 1;
  int currentXp = 0;
  int nextLevelXp = 100;
  List<Map<String, dynamic>> quests = [];
  List<Map<String, String>> chatHistory = [];

  bool isListening = false;
  bool isForegroundRunning = false;

  @override
  void initState() {
    super.initState();
    _requestPermissions();
    _loadRpgData();
    _initForegroundTask();
  }

  Future<void> _requestPermissions() async {
    await [
      Permission.microphone,
      Permission.notification,
    ].request();
  }

  Future<void> _loadRpgData() async {
    try {
      // Perfil
      final profileRes = await supabase.from('user_profile').select().limit(1);
      if (profileRes.isNotEmpty) {
        setState(() {
          level = profileRes[0]['level'] ?? 1;
          currentXp = profileRes[0]['current_xp'] ?? 0;
          nextLevelXp = profileRes[0]['next_level_xp'] ?? 100;
        });
      }

      // Misiones pendientes
      final questsRes = await supabase
          .from('quests')
          .select()
          .eq('status', 'pending')
          .order('created_at', ascending: false)
          .limit(5);

      setState(() {
        quests = List<Map<String, dynamic>>.from(questsRes);
      });
    } catch (e) {
      debugPrint("Error cargando Supabase: $e");
    }
  }

  void _initForegroundTask() {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'abby_voice_channel',
        channelName: 'Abby Servicio en Segundo Plano',
        channelDescription: 'Escucha continua del wake word Abby',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        iconData: const NotificationIconData(
          resType: ResourceType.mipmap,
          resPrefix: ResourcePrefix.ic,
          name: 'launcher',
        ),
      ),
      iosNotificationOptions: const IOSNotificationOptions(),
      foregroundTaskOptions: const ForegroundTaskOptions(
        interval: 5000,
        isOnceEvent: false,
        autoRunOnBoot: true,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  Future<void> _toggleForegroundService() async {
    if (await FlutterForegroundTask.isRunningService) {
      await FlutterForegroundTask.stopService();
      setState(() => isForegroundRunning = false);
    } else {
      await FlutterForegroundTask.startService(
        notificationTitle: 'Abby activa',
        notificationText: 'Escuchando en segundo plano...',
        callback: startCallback,
      );
      setState(() => isForegroundRunning = true);
    }
  }

  Future<void> _onMicTap() async {
    if (isListening) {
      await _speech.stop();
      setState(() => isListening = false);
      return;
    }

    bool available = await _speech.initialize(
      onError: (val) => setState(() => isListening = false),
      onStatus: (val) {
        if (val == 'notListening' || val == 'done') {
          setState(() => isListening = false);
        }
      },
    );

    if (available) {
      setState(() => isListening = true);
      _speech.listen(
        localeId: 'es_MX',
        onResult: (val) async {
          if (val.finalResult) {
            String command = val.recognizedWords;
            setState(() {
              isListening = false;
              chatHistory.insert(0, {"sender": "user", "text": command});
            });

            // Enviar al PC
            String reply = await AbbyService.sendCommand(command);

            setState(() {
              chatHistory.insert(0, {"sender": "abby", "text": reply});
            });

            // Leer en voz alta
            await _tts.speak(reply);

            // Recargar XP y misiones
            _loadRpgData();
          }
        },
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    double progress = (currentXp / nextLevelXp).clamp(0.0, 1.0);

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.shield, color: Color(0xFF00CEC9)),
            SizedBox(width: 8),
            Text('Abby - Game Master', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        backgroundColor: const Color(0xFF1E2130),
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(
              isForegroundRunning ? Icons.notifications_active : Icons.notifications_off,
              color: isForegroundRunning ? Colors.greenAccent : Colors.grey,
            ),
            tooltip: 'Segundo Plano (Wake Word)',
            onPressed: _toggleForegroundService,
          )
        ],
      ),
      body: Column(
        children: [
          // 1. BARRA RPG / STATUS
          Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF1E2130),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF6C5CE7).withOpacity(0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("NIVEL $level", style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF00CEC9))),
                    Text("$currentXp / $nextLevelXp XP", style: const TextStyle(color: Colors.white70)),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 12,
                    backgroundColor: Colors.black38,
                    valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF6C5CE7)),
                  ),
                ),
              ],
            ),
          ),

          // 2. MISIONES ACTIVAS
          if (quests.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: [
                  const Icon(Icons.assignment, size: 18, color: Colors.amber),
                  const SizedBox(width: 6),
                  Text("Misiones Activas (${quests.length})", style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.amber)),
                ],
              ),
            ),
          if (quests.isNotEmpty)
            SizedBox(
              height: 70,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemCount: quests.length,
                itemBuilder: (context, index) {
                  final q = quests[index];
                  return Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF25293E),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(q['title'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                        Text("+${q['xp_reward']} XP", style: const TextStyle(color: Colors.greenAccent, fontSize: 11)),
                      ],
                    ),
                  );
                },
              ),
            ),

          const Divider(color: Colors.white10),

          // 3. HISTORIAL DE CONVERSACIÓN
          Expanded(
            child: ListView.builder(
              reverse: true,
              padding: const EdgeInsets.all(16),
              itemCount: chatHistory.length,
              itemBuilder: (context, index) {
                final item = chatHistory[index];
                bool isUser = item["sender"] == "user";
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.all(12),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF6C5CE7) : const Color(0xFF25293E),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(
                      item["text"] ?? "",
                      style: const TextStyle(fontSize: 14, color: Colors.white),
                    ),
                  ),
                );
              },
            ),
          ),

          // 4. BOTÓN CENTRAL DE VOZ (MICROFONO)
          Container(
            padding: const EdgeInsets.only(bottom: 24, top: 8),
            child: GestureDetector(
              onTap: _onMicTap,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: 76,
                height: 76,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isListening ? Colors.redAccent : const Color(0xFF6C5CE7),
                  boxShadow: [
                    BoxShadow(
                      color: (isListening ? Colors.redAccent : const Color(0xFF6C5CE7)).withOpacity(0.5),
                      blurRadius: isListening ? 25 : 12,
                      spreadRadius: isListening ? 6 : 2,
                    )
                  ],
                ),
                child: Icon(
                  isListening ? Icons.mic : Icons.mic_none,
                  color: Colors.white,
                  size: 38,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
