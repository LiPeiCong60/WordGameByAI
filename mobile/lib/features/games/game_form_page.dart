import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';

class GameFormPage extends StatefulWidget {
  const GameFormPage({super.key, required this.api});
  final ApiClient api;

  @override
  State<GameFormPage> createState() => _GameFormPageState();
}

class _GameFormPageState extends State<GameFormPage> {
  final _title = TextEditingController();
  final _genre = TextEditingController();
  final _worldType = TextEditingController();
  final _tone = TextEditingController();
  final _perspective = TextEditingController(text: '第二人称');
  final _style = TextEditingController();
  final _rules = TextEditingController();
  final _state = TextEditingController();
  List<dynamic> _templates = [];
  int? _templateId;
  bool _loading = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _loadTemplates();
  }

  Future<void> _loadTemplates() async {
    try {
      final value = await widget.api.getList('/templates');
      if (mounted) setState(() => _templates = value);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    }
  }

  void _applyTemplate(int? id) {
    setState(() => _templateId = id);
    if (id == null) return;
    final template = _templates
        .cast<Map<String, dynamic>>()
        .where((item) => item['id'] == id)
        .firstOrNull;
    if (template == null) return;
    _genre.text = template['genre']?.toString() ?? '';
    _worldType.text = template['world_type']?.toString() ?? '';
    _tone.text = template['tone']?.toString() ?? '';
    _style.text = template['default_style_guide']?.toString() ?? '';
    _rules.text = template['default_rules']?.toString() ?? '';
    if (_title.text.trim().isEmpty) _title.text = '${template['name']}存档';
  }

  Future<void> _save() async {
    if (_title.text.trim().isEmpty) {
      setState(() => _error = '请填写存档标题。');
      return;
    }
    setState(() {
      _loading = true;
      _error = '';
    });
    try {
      final game = await widget.api.postJson('/games', {
        'title': _title.text.trim(),
        'template_id': _templateId,
        'genre': _genre.text.trim(),
        'world_type': _worldType.text.trim(),
        'tone': _tone.text.trim(),
        'narrative_perspective': _perspective.text.trim(),
        'style_guide': _style.text.trim(),
        'rules_summary': _rules.text.trim(),
        'current_state': _state.text.trim(),
      });
      if (mounted) Navigator.pop(context, game);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Widget _field(String label, TextEditingController controller,
          {int lines = 1}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
            controller: controller,
            maxLines: lines,
            decoration: InputDecoration(labelText: label)),
      );

  @override
  void dispose() {
    for (final item in [
      _title,
      _genre,
      _worldType,
      _tone,
      _perspective,
      _style,
      _rules,
      _state
    ]) {
      item.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('创建存档')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          DropdownButtonFormField<int?>(
            initialValue: _templateId,
            decoration: const InputDecoration(labelText: '世界模板'),
            items: [
              const DropdownMenuItem<int?>(value: null, child: Text('不使用模板')),
              ..._templates.map((item) => DropdownMenuItem<int?>(
                  value: item['id'] as int,
                  child: Text(item['name']?.toString() ?? '模板')))
            ],
            onChanged: _applyTemplate,
          ),
          const SizedBox(height: 12),
          _field('标题 *', _title),
          _field('题材', _genre),
          _field('世界类型', _worldType),
          _field('故事基调', _tone),
          _field('叙事视角', _perspective),
          _field('文风规则', _style, lines: 4),
          _field('世界规则摘要', _rules, lines: 4),
          _field('初始状态', _state, lines: 3),
          if (_error.isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error,
                    style:
                        TextStyle(color: Theme.of(context).colorScheme.error))),
          FilledButton.icon(
              onPressed: _loading ? null : _save,
              icon: const Icon(Icons.save_outlined),
              label: Text(_loading ? '创建中…' : '创建并进入游戏')),
        ]),
      );
}
