import 'package:flutter/foundation.dart';

import '../models/chat.dart';
import '../services/flask_api_service.dart';

class ChatProvider extends ChangeNotifier {
  final FlaskApiService _api;

  ChatProvider(this._api);

  bool _loadingConversations = false;
  String? _conversationsError;
  List<Conversation> _conversations = const [];

  bool _loadingMessages = false;
  String? _messagesError;
  int? _activeUserId;
  List<ChatMessage> _messages = const [];

  bool get isLoadingConversations => _loadingConversations;
  String? get conversationsError => _conversationsError;
  List<Conversation> get conversations => _conversations;

  bool _sending = false;
  String? _sendError;

  bool get isLoadingMessages => _loadingMessages;
  String? get messagesError => _messagesError;
  int? get activeUserId => _activeUserId;
  List<ChatMessage> get messages => _messages;
  bool get isSending => _sending;
  String? get sendError => _sendError;

  Future<void> loadConversations() async {
    if (_loadingConversations) return;
    _loadingConversations = true;
    _conversationsError = null;
    notifyListeners();
    try {
      _conversations = await _api.fetchSellerConversations();
    } catch (e) {
      _conversationsError = e.toString();
    } finally {
      _loadingConversations = false;
      notifyListeners();
    }
  }

  Future<void> loadMessages(int userId) async {
    if (_loadingMessages && _activeUserId == userId) return;
    _loadingMessages = true;
    _messagesError = null;
    _activeUserId = userId;
    notifyListeners();
    try {
      _messages = await _api.fetchSellerChatMessages(userId);
    } catch (e) {
      _messagesError = e.toString();
    } finally {
      _loadingMessages = false;
      notifyListeners();
    }
  }

  /// Sends a message to the active user thread via REST.
  /// After SocketIO is connected, the echo arrives via [onNewMessage] stream
  /// and the UI can append it without reloading the full thread.
  Future<bool> sendMessage(int userId, String text) async {
    if (text.trim().isEmpty) return false;
    _sending = true;
    _sendError = null;
    notifyListeners();
    try {
      await _api.sendSellerChatMessage(userId, text.trim());
      return true;
    } catch (e) {
      _sendError = e.toString();
      return false;
    } finally {
      _sending = false;
      notifyListeners();
    }
  }

  void clearThread() {
    _activeUserId = null;
    _messages = const [];
    _messagesError = null;
    notifyListeners();
  }

  void reset() {
    _conversations = const [];
    _messages = const [];
    _conversationsError = null;
    _messagesError = null;
    _activeUserId = null;
    notifyListeners();
  }
}
