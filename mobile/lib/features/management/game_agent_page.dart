import 'dart:convert';

import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';

class GameAgentPage extends StatefulWidget {
  const GameAgentPage({super.key, required this.api, required this.gameId});
  final ApiClient api;
  final int gameId;
  @override
  State<GameAgentPage> createState() => _GameAgentPageState();
}

class _GameAgentPageState extends State<GameAgentPage> {
  final _message = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  List<dynamic> _sessions = [];
  int? _sessionId;
  late String _scope = widget.gameId == 0 ? '模板' : '综合管理';
  bool _sending = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    try {
      final sessions = await widget.api
          .getList('/games/${widget.gameId}/management/sessions');
      if (sessions.isEmpty) {
        final made = await widget.api.postJson(
            '/games/${widget.gameId}/management/sessions',
            {'title': 'App 管理对话'});
        sessions.add(made);
      }
      if (mounted) {
        setState(() {
          _sessions = sessions;
          _sessionId ??= sessions.first['id'] as int;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  Future<void> _newSession() async {
    try {
      final made = await widget.api.postJson(
          '/games/${widget.gameId}/management/sessions',
          {'title': 'App 管理对话 ${DateTime.now().month}/${DateTime.now().day}'});
      await _loadSessions();
      if (mounted) {
        setState(() {
          _sessionId = made['id'] as int;
          _messages.clear();
        });
      }
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _send() async {
    final text = _message.text.trim();
    if (text.isEmpty || _sending || _sessionId == null) return;
    setState(() {
      _sending = true;
      _error = '';
      _messages.add({'role': 'user', 'text': text});
      _message.clear();
    });
    try {
      final result = await widget.api.postJson(
          '/management/sessions/$_sessionId/chat',
          {'message': text, 'scope': _scope});
      if (mounted) {
        setState(() => _messages.add({
              'role': 'assistant',
              'text': result['reply']?.toString() ?? '已收到。',
              'proposal':
                  result['requires_confirmation'] == true ? result : null
            }));
      }
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _proposal(Map<String, dynamic> proposal, bool apply) async {
    try {
      final id = proposal['proposal_id'];
      final result = await widget.api
          .postJson('/management/proposals/$id/${apply ? 'apply' : 'reject'}');
      if (mounted) {
        setState(() {
          proposal['resolved'] = true;
          _messages.add({
            'role': 'status',
            'text': apply ? '修改方案已执行：${jsonEncode(result)}' : '修改方案已拒绝。'
          });
        });
      }
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _rag() async {
    final action = await showModalBottomSheet<String>(
        context: context,
        showDragHandle: true,
        builder: (c) => SafeArea(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
              ListTile(
                  leading: const Icon(Icons.list_alt),
                  title: const Text('查看记忆库'),
                  onTap: () => Navigator.pop(c, 'list')),
              ListTile(
                  leading: const Icon(Icons.search),
                  title: const Text('搜索记忆'),
                  onTap: () => Navigator.pop(c, 'search')),
              ListTile(
                  leading: const Icon(Icons.manage_search),
                  title: const Text('重建记忆索引'),
                  onTap: () => Navigator.pop(c, 'rebuild'))
            ])));
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
          builder: (c) => AlertDialog(
                  title: const Text('搜索记忆'),
                  content: TextField(
                      controller: controller,
                      decoration: const InputDecoration(labelText: '关键词')),
                  actions: [
                    FilledButton(
                        onPressed: () =>
                            Navigator.pop(c, controller.text.trim()),
                        child: const Text('搜索'))
                  ]));
      controller.dispose();
      if (query?.isNotEmpty == true) {
        final result = await widget.api.postJson(
            '/games/${widget.gameId}/rag/search',
            {'query': query, 'top_k': 10});
        _showJson('搜索结果', result);
      }
    } catch (e) {
      _snack(e);
    }
  }

  void _showJson(String title, Object data) {
    if (!mounted) return;
    showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
                title: Text(title),
                content: SizedBox(
                    width: double.maxFinite,
                    child: SingleChildScrollView(
                        child: SelectableText(
                            const JsonEncoder.withIndent('  ').convert(data)))),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c),
                      child: const Text('关闭'))
                ]));
  }

  void _snack(Object e) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
    }
  }

  @override
  void dispose() {
    _message.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(widget.gameId == 0 ? '模板智能助手' : '存档智能助手'),
          actions: [
            if (widget.gameId != 0)
              IconButton(
                  onPressed: _rag,
                  tooltip: 'RAG 记忆',
                  icon: const Icon(Icons.memory)),
            IconButton(
                onPressed: _newSession,
                tooltip: '新对话',
                icon: const Icon(Icons.add_comment_outlined)),
          ],
        ),
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      initialValue: _sessionId,
                      decoration: const InputDecoration(labelText: '管理对话'),
                      items: _sessions
                          .map((s) => DropdownMenuItem<int>(
                              value: s['id'] as int,
                              child: Text(s['title']?.toString() ?? '对话')))
                          .toList(),
                      onChanged: (value) => setState(() => _sessionId = value),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _scope,
                      decoration: const InputDecoration(labelText: '作用范围'),
                      items: (widget.gameId == 0
                              ? ['模板']
                              : ['综合管理', '存档', '角色', '世界', '设定'])
                          .map(
                              (v) => DropdownMenuItem(value: v, child: Text(v)))
                          .toList(),
                      onChanged: (value) => setState(() => _scope =
                          value ?? (widget.gameId == 0 ? '模板' : '综合管理')),
                    ),
                  ),
                ],
              ),
            ),
            if (_error.isNotEmpty)
              Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text(_error,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error))),
            Expanded(
              child: _messages.isEmpty
                  ? const Center(
                      child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Text(
                              '你可以让助手设计角色、修改世界、补全设定或调整存档。所有修改都会在你确认后才执行。',
                              textAlign: TextAlign.center)))
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: _messages.length,
                      itemBuilder: (_, index) {
                        final item = _messages[index];
                        final isUser = item['role'] == 'user';
                        final proposal =
                            item['proposal'] as Map<String, dynamic>?;
                        return Align(
                          alignment: isUser
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 520),
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                                color: isUser
                                    ? Theme.of(context)
                                        .colorScheme
                                        .primaryContainer
                                    : Theme.of(context)
                                        .colorScheme
                                        .surfaceContainerHighest,
                                borderRadius: BorderRadius.circular(14)),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SelectableText(
                                      item['text']?.toString() ?? ''),
                                  if (proposal != null &&
                                      proposal['resolved'] != true) ...[
                                    const Divider(),
                                    const Text('助手提出了可执行修改：'),
                                    Text(jsonEncode(
                                        proposal['proposed_actions'])),
                                    Row(children: [
                                      TextButton(
                                          onPressed: () =>
                                              _proposal(proposal, false),
                                          child: const Text('拒绝')),
                                      FilledButton(
                                          onPressed: () =>
                                              _proposal(proposal, true),
                                          child: const Text('确认执行'))
                                    ]),
                                  ],
                                ]),
                          ),
                        );
                      },
                    ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(
                  12, 8, 12, MediaQuery.viewInsetsOf(context).bottom + 12),
              child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Expanded(
                    child: TextField(
                        controller: _message,
                        maxLines: 4,
                        minLines: 1,
                        decoration: const InputDecoration(
                            hintText: '例如：帮我设计一个反复出现的侦探 NPC…'))),
                const SizedBox(width: 8),
                IconButton.filled(
                    onPressed: _sending ? null : _send,
                    icon: _sending
                        ? const SizedBox.square(
                            dimension: 20,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.send)),
              ]),
            ),
          ],
        ),
      );
}
