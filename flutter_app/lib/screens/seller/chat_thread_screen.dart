import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../models/chat.dart';
import '../../providers/chat_provider.dart';

class ChatThreadScreen extends StatefulWidget {
  final int userId;
  final String partnerName;

  const ChatThreadScreen({
    super.key,
    required this.userId,
    required this.partnerName,
  });

  @override
  State<ChatThreadScreen> createState() => _ChatThreadScreenState();
}

class _ChatThreadScreenState extends State<ChatThreadScreen> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<ChatProvider>().loadMessages(widget.userId);
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    // Clear thread state so opening another conversation later starts fresh.
    context.read<ChatProvider>().clearThread();
    super.dispose();
  }

  void _scrollToBottomAfterFrame() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    });
  }

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();

    final title = widget.partnerName.isEmpty
        ? 'User #${widget.userId}'
        : widget.partnerName;

    Widget body;
    if (chat.isLoadingMessages && chat.messages.isEmpty) {
      body = const Center(child: CircularProgressIndicator());
    } else if (chat.messagesError != null && chat.messages.isEmpty) {
      body = Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 12),
              Text(chat.messagesError!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.read<ChatProvider>().loadMessages(widget.userId),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    } else if (chat.messages.isEmpty) {
      body = Center(
        child: Text(
          'No messages yet',
          style: TextStyle(color: Colors.grey[600]),
        ),
      );
    } else {
      _scrollToBottomAfterFrame();
      body = ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: chat.messages.length,
        itemBuilder: (_, i) => _MessageBubble(msg: chat.messages[i]),
      );
    }

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(title: Text(title)),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(child: body),
            _DisabledComposer(),
          ],
        ),
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage msg;
  const _MessageBubble({required this.msg});

  @override
  Widget build(BuildContext context) {
    final fromMe = msg.fromSeller;
    final align = fromMe ? Alignment.centerRight : Alignment.centerLeft;
    final bg    = fromMe ? AppTheme.primaryBlue : Colors.grey.shade200;
    final fg    = fromMe ? Colors.white : Colors.black87;

    return Container(
      alignment: align,
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: Radius.circular(fromMe ? 16 : 4),
              bottomRight: Radius.circular(fromMe ? 4 : 16),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                msg.text,
                style: TextStyle(color: fg, fontSize: 14),
              ),
              if (msg.createdAt != null) ...[
                const SizedBox(height: 4),
                Text(
                  _formatTimestamp(msg.createdAt!),
                  style: TextStyle(
                    color: fg.withValues(alpha: 0.6),
                    fontSize: 10,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  static String _formatTimestamp(String raw) {
    // The backend sends "YYYY-MM-DD HH:MM:SS" — show just the time portion
    // when it's today, otherwise the full date.
    if (raw.length < 16) return raw;
    return raw.substring(0, 16); // "YYYY-MM-DD HH:MM"
  }
}

/// Composer placeholder. Sending lands in the next slice — disabled for now
/// so the UI looks complete without misleading the user.
class _DisabledComposer extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade300)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              enabled: false,
              decoration: InputDecoration(
                hintText: 'Sending coming soon — read-only for now',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: null,
            icon: const Icon(Icons.send),
            color: AppTheme.primaryBlue,
          ),
        ],
      ),
    );
  }
}
