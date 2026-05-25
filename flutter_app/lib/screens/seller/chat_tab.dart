import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/chat_provider.dart';
import 'chat_thread_screen.dart';

class ChatTab extends StatefulWidget {
  const ChatTab({super.key});

  @override
  State<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends State<ChatTab> {
  bool _initialFetchScheduled = false;

  void _scheduleInitialFetchWhenReady() {
    if (_initialFetchScheduled) return;
    final auth = context.read<AuthProvider>();
    final hasToken = (auth.backendAccessToken ?? '').isNotEmpty;
    if (auth.isLoading || !hasToken) return;
    _initialFetchScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<ChatProvider>().loadConversations();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _scheduleInitialFetchWhenReady();
  }

  @override
  Widget build(BuildContext context) {
    context.watch<AuthProvider>();
    final chat = context.watch<ChatProvider>();

    if (chat.isLoadingConversations && chat.conversations.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (chat.conversationsError != null && chat.conversations.isEmpty) {
      return _ErrorView(
        message: chat.conversationsError!,
        onRetry: () => context.read<ChatProvider>().loadConversations(),
      );
    }

    return RefreshIndicator(
      onRefresh: () => context.read<ChatProvider>().loadConversations(),
      child: chat.conversations.isEmpty
          ? _EmptyState()
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: chat.conversations.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final c = chat.conversations[i];
                final hasUnread = c.unreadCount > 0;
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: AppTheme.primaryBlue.withValues(alpha: 0.15),
                    child: Text(
                      c.name.isNotEmpty ? c.name[0].toUpperCase() : '?',
                      style: const TextStyle(
                        color: AppTheme.primaryBlue,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  title: Text(
                    c.name.isEmpty ? 'User #${c.userId}' : c.name,
                    style: TextStyle(
                      fontWeight: hasUnread ? FontWeight.w700 : FontWeight.w600,
                    ),
                  ),
                  subtitle: Text(
                    c.lastMessage,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: hasUnread ? Colors.black87 : Colors.grey[600],
                    ),
                  ),
                  trailing: hasUnread
                      ? Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryBlue,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${c.unreadCount}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        )
                      : const Icon(Icons.chevron_right, color: Colors.grey),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ChatThreadScreen(
                        userId: c.userId,
                        partnerName: c.name,
                      ),
                    ),
                  ),
                );
              },
            ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 80, horizontal: 32),
      children: [
        Icon(Icons.chat_bubble_outline, size: 72, color: Colors.grey[400]),
        const SizedBox(height: 16),
        Text(
          'No conversations yet',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Colors.grey[700],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Buyer messages will show up here.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey[600]),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
