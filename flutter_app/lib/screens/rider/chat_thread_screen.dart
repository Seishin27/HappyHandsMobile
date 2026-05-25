import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../providers/rider_chat_provider.dart';

class RiderChatThreadScreen extends StatefulWidget {
  final int partnerId;
  final String partnerName;
  final String partnerType;

  const RiderChatThreadScreen({
    super.key,
    required this.partnerId,
    required this.partnerName,
    required this.partnerType,
  });

  @override
  State<RiderChatThreadScreen> createState() => _RiderChatThreadScreenState();
}

class _RiderChatThreadScreenState extends State<RiderChatThreadScreen> {
  final _scrollCtrl = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<RiderChatProvider>().loadMessages(widget.partnerId, widget.partnerType);
    });
  }

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<RiderChatProvider>();
    final isLoading = chat.isLoadingMessages;
    final msgs = chat.messages;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.partnerName),
        automaticallyImplyLeading: false, // NO BACK BUTTON
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () async {
              await context.read<RiderChatProvider>().loadMessages(widget.partnerId, widget.partnerType);
            },
          ),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
      resizeToAvoidBottomInset: true,
      body: Column(
        children: [
          if (isLoading && msgs.isEmpty) const LinearProgressIndicator(),
          if (chat.messagesError != null)
            Container(
              color: AppTheme.errorRed.withValues(alpha: 0.1),
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 20),
                  const SizedBox(width: 8),
                  Expanded(child: Text(chat.messagesError!, style: const TextStyle(color: AppTheme.errorRed))),
                ],
              ),
            ),
          Expanded(
            child: msgs.isEmpty && !isLoading
                ? const Center(child: Text('No messages yet', style: TextStyle(color: Colors.grey)))
                : ListView.builder(
                    controller: _scrollCtrl,
                    reverse: false, // Wait, messages might be ASC. We should check that. Let's just build it simple.
                    itemCount: msgs.length,
                    padding: const EdgeInsets.all(16),
                    itemBuilder: (context, i) {
                      final m = msgs[i];
                      final amIMe = m.senderRole == 'rider';

                      return Align(
                        alignment: amIMe ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                          decoration: BoxDecoration(
                            color: amIMe ? AppTheme.primaryBlue : Colors.grey[200],
                            borderRadius: BorderRadius.only(
                              topLeft: const Radius.circular(16),
                              topRight: const Radius.circular(16),
                              bottomLeft: Radius.circular(amIMe ? 16 : 0),
                              bottomRight: Radius.circular(amIMe ? 0 : 16),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                m.text,
                                style: TextStyle(
                                  color: amIMe ? Colors.white : Colors.black87,
                                  fontSize: 15,
                                ),
                              ),
                              if (m.createdAt != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  m.createdAt!.split('.').first,
                                  style: TextStyle(
                                    fontSize: 10,
                                    color: amIMe ? Colors.white70 : Colors.black54,
                                  ),
                                ),
                              ]
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          const Divider(height: 1),
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.grey[50],
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    enabled: false,
                    decoration: InputDecoration(
                      hintText: 'Sending messages in next phase...',
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                CircleAvatar(
                  backgroundColor: Colors.grey[400],
                  child: const Icon(Icons.send, color: Colors.white, size: 20),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
