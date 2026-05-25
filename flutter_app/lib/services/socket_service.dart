import 'dart:async';
import 'dart:developer' as developer;

import 'package:socket_io_client/socket_io_client.dart' as io;

import '../core/config/app_config.dart';

/// Connects to the Flask-SocketIO server using the JWT access token.
///
/// The server already handles JWT auth via the `token` query parameter
/// (see chat_socket.py `_auth_from_socket()`), so no server changes are needed.
///
/// Usage:
///   final socket = SocketService();
///   socket.connect(token: jwtToken, userId: 42, role: 'user');
///   socket.onOrderUpdate.listen((data) => ...);
///   socket.onNewMessage.listen((data) => ...);
class SocketService {
  io.Socket? _socket;
  bool _connected = false;

  bool get isConnected => _connected;

  final _orderUpdateController = StreamController<Map<String, dynamic>>.broadcast();
  final _newMessageController = StreamController<Map<String, dynamic>>.broadcast();
  final _notificationController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get onOrderUpdate => _orderUpdateController.stream;
  Stream<Map<String, dynamic>> get onNewMessage => _newMessageController.stream;
  Stream<Map<String, dynamic>> get onNotification => _notificationController.stream;

  /// Connects to the SocketIO server and joins the appropriate room.
  /// Call this after login.
  void connect({required String token, required int userId, required String role}) {
    if (_connected) return;

    final serverUrl = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/api/?$'), '');

    _socket = io.io(
      serverUrl,
      io.OptionBuilder()
          .setTransports(['websocket'])
          .setQuery({'token': token, 'role': role})
          .enableAutoConnect()
          .enableReconnection()
          .setReconnectionAttempts(5)
          .setReconnectionDelay(2000)
          .build(),
    );

    _socket!.onConnect((_) {
      _connected = true;
      developer.log('SocketService: connected');
      // Join role-specific room (matches web pattern: user_42, seller_7, etc.)
      _socket!.emit('join', {'room': '${role}_$userId'});
    });

    _socket!.onDisconnect((_) {
      _connected = false;
      developer.log('SocketService: disconnected');
    });

    _socket!.onConnectError((err) {
      developer.log('SocketService: connect error $err');
    });

    // Order status updates emitted by the backend when a seller/rider changes status
    _socket!.on('order_status_changed', (data) {
      if (data is Map && !_orderUpdateController.isClosed) {
        _orderUpdateController.add(Map<String, dynamic>.from(data));
      }
    });

    // New chat messages
    _socket!.on('chat_message', (data) {
      if (data is Map && !_newMessageController.isClosed) {
        _newMessageController.add(Map<String, dynamic>.from(data));
      }
    });

    // General notifications (order placed, payment confirmed, etc.)
    _socket!.on('notification', (data) {
      if (data is Map && !_notificationController.isClosed) {
        _notificationController.add(Map<String, dynamic>.from(data));
      }
    });

    _socket!.connect();
  }

  /// Sends a chat message via SocketIO (mirrors the web client behaviour).
  void sendChatMessage({
    required String room,
    required String text,
    required String senderRole,
    required int senderId,
  }) {
    _socket?.emit('chat_message', {
      'room': room,
      'message': text,
      'sender_role': senderRole,
      'sender_id': senderId,
    });
  }

  void disconnect() {
    _socket?.disconnect();
    _socket?.dispose();
    _socket = null;
    _connected = false;
  }

  void dispose() {
    disconnect();
    _orderUpdateController.close();
    _newMessageController.close();
    _notificationController.close();
  }
}
