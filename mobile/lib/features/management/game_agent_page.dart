import 'dart:convert';

import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';

class GameAgentPage extends StatefulWidget {
  const GameAgentPage({
    super.key,
    required this.api,
    required this.gameId,
    this.templateContext,
  });

  final ApiClient api;
  final int gameId;
  final Map<String, dynamic>? templateContext;

  @override
  State<GameAgentPage> createState() => _GameAgentPageState();
}

class _GameAgentPageState extends State<GameAgentPage> {
  final _message = TextEditingController();
  final _scroll = ScrollController();
  final List<Map<String, dynamic>> _messages = [];
  List<dynamic> _sessions = [];
  int? _sessionId;
  late String _scope = widget.gameId == 0 ? '模板' : '综合管理';
  bool _sending = false;
  bool _loadingSessions = true;
  bool _loadingHistory = false;
  bool _didApplyChanges = false;
  int _historyEpoch = 0;
  String _error = '';

  bool get _isTemplateMode => widget.gameId == 0;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions({int? preferredId}) async {
    try {
      final sessions = List<dynamic>.from(await widget.api
          .getList('/games/${widget.gameId}/management/sessions'));
      if (sessions.isEmpty) {
        final made = await widget.api.postJson(
          '/games/${widget.gameId}/management/sessions',
          {'title': _isTemplateMode ? '模板设计对话' : 'App 管理对话'},
        );
        sessions.add(made);
      }
      final currentId = preferredId ?? _sessionId;
      final selectedId = sessions
              .where((item) => item['id'] == currentId)
              .map<int>((item) => item['id'] as int)
              .firstOrNull ??
          sessions.first['id'] as int;
      if (!mounted) return;
      setState(() {
        _sessions = sessions;
        _sessionId = selectedId;
        _loadingSessions = false;
        _error = '';
      });
      await _loadMessages(selectedId);
    } catch (error) {
      if (mounted) {
        setState(() {
          _loadingSessions = false;
          _error = apiErrorMessage(error);
        });
      }
    }
  }

  Future<void> _loadMessages(int sessionId) async {
    final epoch = ++_historyEpoch;
    setState(() {
      _loadingHistory = true;
      _messages.clear();
      _error = '';
    });
    try {
      final turns =
          await widget.api.getList('/management/sessions/$sessionId/messages');
      final loaded = <Map<String, dynamic>>[];
      for (final raw in turns) {
        final turn = (raw as Map).cast<String, dynamic>();
        final request = turn['user_request']?.toString().trim() ?? '';
        final response = turn['agent_response']?.toString().trim() ?? '';
        if (request.isNotEmpty) {
          loaded.add({'role': 'user', 'text': request});
        }
        if (response.isNotEmpty) {
          loaded.add({
            'role': 'assistant',
            'text': response,
            'proposal': turn['requires_confirmation'] == true
                ? <String, dynamic>{
                    'proposal_id': turn['proposal_id'],
                    'proposed_actions': turn['proposed_actions'] ?? const [],
                    'resolved': false,
                  }
                : null,
          });
        }
      }
      if (!mounted || epoch != _historyEpoch || _sessionId != sessionId) {
        return;
      }
      setState(() => _messages.addAll(loaded));
      _scrollToBottom();
    } catch (error) {
      if (mounted && epoch == _historyEpoch && _sessionId == sessionId) {
        setState(() => _error = apiErrorMessage(error));
      }
    } finally {
      if (mounted && epoch == _historyEpoch && _sessionId == sessionId) {
        setState(() => _loadingHistory = false);
      }
    }
  }

  Future<void> _selectSession(int? value) async {
    if (value == null || value == _sessionId) return;
    setState(() => _sessionId = value);
    await _loadMessages(value);
  }

  Future<void> _newSession() async {
    try {
      final now = DateTime.now();
      final made = await widget.api.postJson(
        '/games/${widget.gameId}/management/sessions',
        {
          'title': _isTemplateMode
              ? '模板设计 ${now.month}/${now.day}'
              : 'App 管理对话 ${now.month}/${now.day}'
        },
      );
      await _loadSessions(preferredId: made['id'] as int);
    } catch (error) {
      _snack(error);
    }
  }

  String _requestWithContext(String text) {
    final context = widget.templateContext;
    if (!_isTemplateMode || context == null || context.isEmpty) return text;
    return '【当前编辑上下文】\n${jsonEncode(context)}\n\n【用户请求】\n$text';
  }

  Future<void> _send() async {
    final text = _message.text.trim();
    final activeSession = _sessionId;
    if (text.isEmpty || _sending || _loadingHistory || activeSession == null) {
      return;
    }
    setState(() {
      _sending = true;
      _error = '';
      _messages.add({'role': 'user', 'text': text});
      _message.clear();
    });
    _scrollToBottom();
    try {
      final result = await widget.api.postJson(
        '/management/sessions/$activeSession/chat',
        {'message': _requestWithContext(text), 'scope': _scope},
      );
      if (!mounted || _sessionId != activeSession) return;
      setState(() => _messages.add({
            'role': 'assistant',
            'text': result['reply']?.toString() ?? '已收到。',
            'proposal': result['requires_confirmation'] == true
                ? Map<String, dynamic>.from(result)
                : null,
          }));
      _scrollToBottom();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = apiErrorMessage(error);
          _messages.add({
            'role': 'status',
            'text': '发送失败：${apiErrorMessage(error)}',
          });
        });
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _proposal(Map<String, dynamic> proposal, bool apply) async {
    if (proposal['busy'] == true) return;
    setState(() => proposal['busy'] = true);
    try {
      final id = proposal['proposal_id'];
      await widget.api
          .postJson('/management/proposals/$id/${apply ? 'apply' : 'reject'}');
      if (!mounted) return;
      setState(() {
        proposal['resolved'] = true;
        proposal['busy'] = false;
        if (apply) _didApplyChanges = true;
        _messages.add({
          'role': 'status',
          'text': apply
              ? (_isTemplateMode ? '模板方案已创建或更新，可以返回模板列表查看。' : '修改方案已执行。')
              : '修改方案已拒绝。',
        });
      });
      _scrollToBottom();
    } catch (error) {
      if (mounted) setState(() => proposal['busy'] = false);
      _snack(error);
    }
  }

  int _characterCount(Object? value) {
    Object? parsed = value;
    if (value is String) {
      try {
        parsed = jsonDecode(value);
      } catch (_) {
        return 0;
      }
    }
    if (parsed is List) return parsed.length;
    if (parsed is Map && parsed['characters'] is List) {
      return (parsed['characters'] as List).length;
    }
    return 0;
  }

  String _proposalSummary(Object? value) {
    if (value is! List || value.isEmpty) return '已准备一项可执行修改。';
    final lines = <String>[];
    for (final raw in value) {
      if (raw is! Map) continue;
      final action = raw['action']?.toString() ?? '';
      final fields = raw['fields'] is Map ? raw['fields'] as Map : const {};
      final name = fields['name']?.toString().trim();
      final actionLabel = switch (action) {
        'create_template' => '创建模板',
        'update_template' => '更新模板',
        'delete_template' => '删除模板',
        'create_character' => '创建角色',
        'update_character' => '更新角色',
        'delete_character' => '删除角色',
        _ => '执行修改',
      };
      final characters = _characterCount(fields['default_character_fields']);
      lines.add(
        '• $actionLabel${name?.isNotEmpty == true ? '「$name」' : ''}'
        '${characters > 0 ? ' · $characters 位开局角色' : ''}',
      );
    }
    return lines.isEmpty ? '已准备一项可执行修改。' : lines.join('\n');
  }

  void _sendPreset(String text) {
    _message.text = text;
    _send();
  }

  Future<void> _rag() async {
    final action = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            leading: const Icon(Icons.list_alt),
            title: const Text('查看记忆库'),
            onTap: () => Navigator.pop(context, 'list'),
          ),
          ListTile(
            leading: const Icon(Icons.search),
            title: const Text('搜索记忆'),
            onTap: () => Navigator.pop(context, 'search'),
          ),
          ListTile(
            leading: const Icon(Icons.manage_search),
            title: const Text('重建记忆索引'),
            onTap: () => Navigator.pop(context, 'rebuild'),
          ),
        ]),
      ),
    );
    if (action == null) return;
    try {
      if (action == 'rebuild') {
        final result =
            await widget.api.postJson('/games/${widget.gameId}/rag/rebuild');
        _showJson('索引重建完成', result);
        return;
      }
      if (action == 'list') {
        final result =
            await widget.api.getList('/games/${widget.gameId}/rag/memories');
        _showJson('记忆库（${result.length}）', result);
        return;
      }
      final controller = TextEditingController();
      if (!mounted) return;
      final query = await showDialog<String>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('搜索记忆'),
          content: TextField(
            controller: controller,
            decoration: const InputDecoration(labelText: '关键词'),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context, controller.text.trim()),
              child: const Text('搜索'),
            ),
          ],
        ),
      );
      controller.dispose();
      if (query?.isNotEmpty == true) {
        final result = await widget.api.postJson(
          '/games/${widget.gameId}/rag/search',
          {'query': query, 'top_k': 10},
        );
        _showJson('搜索结果', result);
      }
    } catch (error) {
      _snack(error);
    }
  }

  void _showJson(String title, Object data) {
    if (!mounted) return;
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: double.maxFinite,
          child: SingleChildScrollView(
            child: SelectableText(
              const JsonEncoder.withIndent('  ').convert(data),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    });
  }

  void _snack(Object error) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(apiErrorMessage(error))),
      );
    }
  }

  Widget _emptyState(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    if (!_isTemplateMode) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            '你可以让助手设计角色、修改世界、补全设定或调整存档。所有修改都会在你确认后才执行。',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.auto_awesome, size: 38, color: colors.primary),
          const SizedBox(height: 12),
          Text(
            '描述一个世界或故事概念，助手会自动补全规则、文风和开局角色，并生成待确认的完整模板。',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.5),
          ),
          const SizedBox(height: 18),
          Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                ActionChip(
                  label: const Text('滨海小城恋爱'),
                  onPressed: () => _sendPreset('生成一个滨海小城的恋爱模板，细节由你自动补全。'),
                ),
                ActionChip(
                  label: const Text('悬疑侦探'),
                  onPressed: () => _sendPreset('生成一个反复出现线索的悬疑侦探模板。'),
                ),
                ActionChip(
                  label: const Text('奇幻冒险'),
                  onPressed: () => _sendPreset('生成一个角色成长驱动的奇幻冒险模板。'),
                ),
              ]),
        ]),
      ),
    );
  }

  @override
  void dispose() {
    _message.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          leading: IconButton(
            onPressed: () => Navigator.pop(context, _didApplyChanges),
            icon: const Icon(Icons.arrow_back),
          ),
          title: Text(_isTemplateMode ? '模板智能助手' : '存档智能助手'),
          actions: [
            if (!_isTemplateMode)
              IconButton(
                onPressed: _rag,
                tooltip: 'RAG 记忆',
                icon: const Icon(Icons.memory),
              ),
            IconButton(
              onPressed: _loadingSessions ? null : _newSession,
              tooltip: '新对话',
              icon: const Icon(Icons.add_comment_outlined),
            ),
          ],
        ),
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: Row(children: [
                Expanded(
                  child: DropdownButtonFormField<int>(
                    key: ValueKey('session-$_sessionId-${_sessions.length}'),
                    initialValue: _sessionId,
                    decoration: InputDecoration(
                      labelText: _isTemplateMode ? '模板设计对话' : '管理对话',
                    ),
                    items: _sessions
                        .map((session) => DropdownMenuItem<int>(
                              value: session['id'] as int,
                              child: Text(session['title']?.toString() ?? '对话'),
                            ))
                        .toList(),
                    onChanged: _loadingHistory ? null : _selectSession,
                  ),
                ),
                if (!_isTemplateMode) ...[
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _scope,
                      decoration: const InputDecoration(labelText: '作用范围'),
                      items: const ['综合管理', '存档', '角色', '世界', '设定']
                          .map((value) => DropdownMenuItem(
                                value: value,
                                child: Text(value),
                              ))
                          .toList(),
                      onChanged: (value) =>
                          setState(() => _scope = value ?? '综合管理'),
                    ),
                  ),
                ],
              ]),
            ),
            if (_loadingHistory || _loadingSessions)
              const LinearProgressIndicator(minHeight: 2),
            if (_error.isNotEmpty)
              Padding(
                padding: const EdgeInsets.all(8),
                child: Text(
                  _error,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            Expanded(
              child: _messages.isEmpty && !_loadingHistory
                  ? _emptyState(context)
                  : ListView.builder(
                      controller: _scroll,
                      padding: const EdgeInsets.all(12),
                      itemCount: _messages.length,
                      itemBuilder: (context, index) {
                        final item = _messages[index];
                        final isUser = item['role'] == 'user';
                        final isStatus = item['role'] == 'status';
                        final proposal =
                            item['proposal'] as Map<String, dynamic>?;
                        final colors = Theme.of(context).colorScheme;
                        return Align(
                          alignment: isUser
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 520),
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.all(13),
                            decoration: BoxDecoration(
                              color: isUser
                                  ? colors.primaryContainer
                                  : isStatus
                                      ? colors.tertiaryContainer
                                      : colors.surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SelectableText(item['text']?.toString() ?? ''),
                                if (proposal != null &&
                                    proposal['resolved'] != true) ...[
                                  const SizedBox(height: 10),
                                  const Divider(),
                                  Text(
                                    '待确认的模板方案',
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleSmall
                                        ?.copyWith(fontWeight: FontWeight.w700),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(_proposalSummary(
                                      proposal['proposed_actions'])),
                                  const SizedBox(height: 8),
                                  Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        TextButton(
                                          onPressed: proposal['busy'] == true
                                              ? null
                                              : () =>
                                                  _proposal(proposal, false),
                                          child: const Text('拒绝'),
                                        ),
                                        const SizedBox(width: 6),
                                        FilledButton.icon(
                                          onPressed: proposal['busy'] == true
                                              ? null
                                              : () => _proposal(proposal, true),
                                          icon: proposal['busy'] == true
                                              ? const SizedBox.square(
                                                  dimension: 14,
                                                  child:
                                                      CircularProgressIndicator(
                                                          strokeWidth: 2),
                                                )
                                              : const Icon(Icons.check,
                                                  size: 18),
                                          label: const Text('确认执行'),
                                        ),
                                      ]),
                                ],
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child:
                    Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Expanded(
                    child: TextField(
                      controller: _message,
                      maxLines: 4,
                      minLines: 1,
                      textInputAction: TextInputAction.newline,
                      decoration: InputDecoration(
                        hintText: _isTemplateMode
                            ? '例如：生成一个滨海小城的恋爱模板…'
                            : '例如：帮我设计一个反复出现的侦探 NPC…',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _sending ||
                            _loadingSessions ||
                            _loadingHistory ||
                            _sessionId == null
                        ? null
                        : _send,
                    icon: _sending
                        ? const SizedBox.square(
                            dimension: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                  ),
                ]),
              ),
            ),
          ],
        ),
      );
}
