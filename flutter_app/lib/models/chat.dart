/// Conversation summary returned by /api/seller/chat/conversations.
class Conversation {
  final int userId;
  final String name;
  final String lastMessage;
  final int lastChatId;
  final int unreadCount;
  final String type;

  const Conversation({
    required this.userId,
    required this.name,
    required this.lastMessage,
    required this.lastChatId,
    required this.unreadCount,
    this.type = 'user',
  });

  factory Conversation.fromJson(Map<String, dynamic> json) {
    return Conversation(
      userId:      (json['userID']      as num?)?.toInt() ?? (json['id']      as num?)?.toInt() ?? 0,
      name:        (json['name']        ?? json['username'] ?? '').toString(),
      lastMessage: (json['lastMessage'] ?? '').toString(),
      lastChatId:  (json['lastChatID']  as num?)?.toInt() ?? 0,
      unreadCount: (json['unreadCount'] as num?)?.toInt() ?? 0,
      type:        (json['type'] ?? 'user').toString(),
    );
  }
}

/// Single chat message returned by /api/seller/chat/messages.
class ChatMessage {
  final int id;
  final int userId;
  final int sellerId;
  final String text;
  final String? image;
  final String senderRole; // 'user' | 'seller'
  final bool fromSeller;
  final bool isRead;
  final String? createdAt;

  const ChatMessage({
    required this.id,
    required this.userId,
    required this.sellerId,
    required this.text,
    required this.senderRole,
    required this.fromSeller,
    required this.isRead,
    this.image,
    this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    final role = (json['sender_role'] ?? 'user').toString();
    return ChatMessage(
      id:         (json['id']        as num?)?.toInt() ?? 0,
      userId:     (json['user_id']   as num?)?.toInt() ?? 0,
      sellerId:   (json['seller_id'] as num?)?.toInt() ?? 0,
      text:       (json['text']      ?? '').toString(),
      image:      json['image']?.toString(),
      senderRole: role,
      fromSeller: (json['from_seller'] is bool)
          ? json['from_seller'] as bool
          : role.toLowerCase() == 'seller',
      isRead:     json['is_read'] == true,
      createdAt:  json['created_at']?.toString(),
    );
  }
}
