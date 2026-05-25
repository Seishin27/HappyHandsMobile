import 'package:flutter/foundation.dart';

import '../models/chat.dart';
import '../services/flask_api_service.dart';

class RiderChatProvider extends ChangeNotifier {
  final FlaskApiService _api;

  RiderChatProvider(this._api);

  bool _loadingConversations = false;
  String? _conversationsError;
  List<Conversation> _conversations = const [];

  bool _loadingMessages = false;
  String? _messagesError;
  int? _activePartnerId;
  String? _activePartnerType;
  List<ChatMessage> _messages = const [];

  bool get isLoadingConversations => _loadingConversations;
  String? get conversationsError => _conversationsError;
  List<Conversation> get conversations => _conversations;

  bool get isLoadingMessages => _loadingMessages;
  String? get messagesError => _messagesError;
  int? get activePartnerId => _activePartnerId;
  String? get activePartnerType => _activePartnerType;
  List<ChatMessage> get messages => _messages;

  Future<void> loadConversations() async {
    if (_loadingConversations) return;
    _loadingConversations = true;
    _conversationsError = null;
    notifyListeners();
    try {
      _conversations = await _api.fetchRiderConversations();
    } catch (e) {
      _conversationsError = e.toString();
    } finally {
      _loadingConversations = false;
      notifyListeners();
    }
  }

  Future<void> loadMessages(int partnerId, String partnerType) async {
    if (_loadingMessages && _activePartnerId == partnerId && _activePartnerType == partnerType) return;
    _loadingMessages = true;
    _messagesError = null;
    _activePartnerId = partnerId;
    _activePartnerType = partnerType;
    notifyListeners();
    try {
      _messages = await _api.fetchRiderChatMessages(partnerId, partnerType);
    } catch (e) {
      _messagesError = e.toString();
    } finally {
      _loadingMessages = false;
      notifyListeners();
    }
  }

  void clearThread() {
    _activePartnerId = null;
    _activePartnerType = null;
    _messages = const [];
    _messagesError = null;
    notifyListeners();
  }

  void reset() {
    _conversations = const [];
    _messages = const [];
    _conversationsError = null;
    _messagesError = null;
    _activePartnerId = null;
    _activePartnerType = null;
    notifyListeners();
  }
}
