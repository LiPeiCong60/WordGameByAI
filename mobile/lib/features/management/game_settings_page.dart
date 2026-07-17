import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';

class GameSettingsPage extends StatefulWidget {
  const GameSettingsPage(
      {super.key,
      required this.api,
      required this.game,
      required this.onUpdated});
  final ApiClient api;
  final Map<String, dynamic> game;
  final ValueChanged<Map<String, dynamic>> onUpdated;

  @override
  State<GameSettingsPage> createState() => _GameSettingsPageState();
}

class _GameSettingsPageState extends State<GameSettingsPage> {
  late final Map<String, TextEditingController> _fields = {
    for (final key in [
      'title',
      'genre',
      'world_type',
      'tone',
      'narrative_perspective',
      'current_state',
      'style_guide',
      'rules_summary'
    ])
      key: TextEditingController(text: widget.game[key]?.toString() ?? ''),
  };
  bool _saving = false;
  String _message = '';

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _message = '';
    });
    try {
      final game = await widget.api.patchJson('/games/${widget.game['id']}', {
        for (final entry in _fields.entries) entry.key: entry.value.text.trim()
      });
      widget.onUpdated(game);
      if (mounted) setState(() => _message = '存档信息已保存。');
    } catch (error) {
      if (mounted) setState(() => _message = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Widget _field(String key, String label, {int lines = 1}) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
            controller: _fields[key],
            maxLines: lines,
            decoration: InputDecoration(labelText: label)),
      );

  @override
  void dispose() {
    for (final item in _fields.values) {
      item.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('存档设置')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          _field('title', '标题'),
          _field('genre', '题材'),
          _field('world_type', '世界类型'),
          _field('tone', '基调'),
          _field('narrative_perspective', '叙事视角'),
          _field('current_state', '当前状态', lines: 4),
          _field('style_guide', '文风规则', lines: 5),
          _field('rules_summary', '世界规则摘要', lines: 5),
          if (_message.isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_message)),
          FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: const Icon(Icons.save_outlined),
              label: Text(_saving ? '保存中…' : '保存存档')),
        ]),
      );
}
