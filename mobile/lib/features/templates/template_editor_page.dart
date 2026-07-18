import 'dart:convert';

import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/ui/character_avatar.dart';
import 'template_character_codec.dart';

class TemplateEditorPage extends StatefulWidget {
  const TemplateEditorPage({
    super.key,
    required this.title,
    required this.initial,
    required this.onSave,
    required this.isAdmin,
  });

  final String title;
  final Map<String, dynamic> initial;
  final Future<void> Function(Map<String, dynamic> data) onSave;
  final bool isAdmin;

  @override
  State<TemplateEditorPage> createState() => _TemplateEditorPageState();
}

class _TemplateEditorPageState extends State<TemplateEditorPage> {
  static const _textFields = <_TemplateField>[
    _TemplateField('name', '模板名称', required: true),
    _TemplateField('genre', '题材'),
    _TemplateField('world_type', '世界类型'),
    _TemplateField('tone', '故事基调'),
    _TemplateField('description', '模板描述', lines: 3),
    _TemplateField('default_style_guide', '默认文风', lines: 5),
    _TemplateField('default_rules', '默认世界规则', lines: 5),
  ];

  final Map<String, TextEditingController> _controllers = {};
  late List<Map<String, dynamic>> _characters;
  late bool _isPublic;
  late bool _characterSourceNeedsReset;
  bool _saving = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    for (final field in _textFields) {
      _controllers[field.key] = TextEditingController(
        text: widget.initial[field.key]?.toString() ?? '',
      );
    }
    _isPublic = widget.initial['is_public'] == true;
    final decoded = TemplateCharacterCodec.decode(
      widget.initial['default_character_fields'],
    );
    _characters = decoded.characters.map((item) => {...item}).toList();
    _characterSourceNeedsReset = decoded.hasError;
  }

  Future<void> _openCharacter({int? index, String role = 'npc'}) async {
    final initial = index == null
        ? TemplateCharacterCodec.blank(role)
        : {..._characters[index]};
    final result = await Navigator.push<Map<String, dynamic>>(
      context,
      MaterialPageRoute(
        builder: (_) => _TemplateCharacterEditorPage(
          title: index == null ? '新增角色' : '编辑角色',
          initial: initial,
        ),
      ),
    );
    if (!mounted || result == null) return;
    setState(() {
      _characterSourceNeedsReset = false;
      if (index == null) {
        _characters.add(result);
      } else {
        _characters[index] = result;
      }
    });
  }

  void _removeCharacter(int index) {
    final removed = _characters[index];
    setState(() {
      _characterSourceNeedsReset = false;
      _characters.removeAt(index);
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('已移除“${removed['name']}”'),
        action: SnackBarAction(
          label: '撤销',
          onPressed: () {
            if (mounted) setState(() => _characters.insert(index, removed));
          },
        ),
      ),
    );
  }

  void _resetCharacters() {
    setState(() {
      _characters = [
        TemplateCharacterCodec.blank('protagonist'),
        TemplateCharacterCodec.blank('npc'),
      ];
      _characterSourceNeedsReset = false;
      _error = '';
    });
  }

  Future<void> _save() async {
    if (_characterSourceNeedsReset) {
      setState(() => _error = '请先重新建立开局角色配置，避免覆盖无法识别的旧数据。');
      return;
    }
    final name = _controllers['name']!.text.trim();
    if (name.isEmpty) {
      setState(() => _error = '请填写模板名称。');
      return;
    }
    final data = <String, dynamic>{
      for (final field in _textFields)
        field.key: _controllers[field.key]!.text.trim(),
      'default_character_fields': TemplateCharacterCodec.encode(_characters),
    };
    if (widget.isAdmin) data['is_public'] = _isPublic;
    setState(() {
      _saving = true;
      _error = '';
    });
    try {
      await widget.onSave(data);
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final protagonistCount =
        _characters.where((item) => item['role_type'] == 'protagonist').length;
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          _sectionTitle(context, '基础设计', Icons.auto_stories_outlined),
          for (final field in _textFields) ...[
            TextField(
              key: ValueKey('template-${field.key}'),
              controller: _controllers[field.key],
              maxLines: field.lines,
              decoration: InputDecoration(
                labelText: '${field.label}${field.required ? ' *' : ''}',
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (widget.isAdmin)
            SwitchListTile(
              key: const ValueKey('template-is-public'),
              contentPadding: const EdgeInsets.symmetric(horizontal: 4),
              title: const Text('公开模板'),
              subtitle: const Text('公开后所有用户均可用，只有管理员可维护。'),
              value: _isPublic,
              onChanged: (value) => setState(() => _isPublic = value),
            ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: _sectionTitle(
                  context,
                  '开局角色',
                  Icons.groups_2_outlined,
                  subtitle: '${_characters.length} 人 · 主角 $protagonistCount 人',
                ),
              ),
            ],
          ),
          if (_characterSourceNeedsReset)
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '原开局角色配置无法识别，已暂停自动覆盖。',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      key: const ValueKey('reset-character-config'),
                      onPressed: _resetCharacters,
                      icon: const Icon(Icons.restart_alt),
                      label: const Text('重新建立角色配置'),
                    ),
                  ],
                ),
              ),
            ),
          if (!_characterSourceNeedsReset && _characters.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(18),
                child: Text('还没有开局角色。可以先添加一位主角和一位重要 NPC。'),
              ),
            ),
          for (var index = 0; index < _characters.length; index++)
            _characterCard(context, _characters[index], index),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  key: const ValueKey('add-protagonist'),
                  onPressed: () => _openCharacter(role: 'protagonist'),
                  icon: const Icon(Icons.person_add_alt_1),
                  label: const Text('添加主角'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.tonalIcon(
                  key: const ValueKey('add-npc'),
                  onPressed: () => _openCharacter(),
                  icon: const Icon(Icons.group_add_outlined),
                  label: const Text('添加 NPC'),
                ),
              ),
            ],
          ),
          if (_error.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(
                _error,
                key: const ValueKey('template-editor-error'),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            border: Border(
              top: BorderSide(
                  color: Theme.of(context).colorScheme.outlineVariant),
            ),
          ),
          child: FilledButton.icon(
            key: const ValueKey('save-template'),
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: Text(_saving ? '保存中…' : '保存模板'),
          ),
        ),
      ),
    );
  }

  Widget _characterCard(
    BuildContext context,
    Map<String, dynamic> character,
    int index,
  ) {
    final protagonist = character['role_type'] == 'protagonist';
    final identity = character['race_or_identity']?.toString() ?? '';
    final personality = character['personality']?.toString() ?? '';
    return Card(
      key: ValueKey('template-character-$index'),
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: CharacterAvatar(
          character: character,
          avatarUrl: character['avatar_url']?.toString() ?? '',
          size: 48,
          showAutoBadge: true,
        ),
        title: Row(
          children: [
            Flexible(
              child: Text(
                character['name']?.toString() ?? '未命名角色',
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Chip(
              visualDensity: VisualDensity.compact,
              label: Text(protagonist ? '主角' : 'NPC'),
            ),
          ],
        ),
        subtitle: Text(
          [identity, personality]
                  .where((item) => item.isNotEmpty)
                  .join(' · ')
                  .isEmpty
              ? '待补充角色设定'
              : [identity, personality]
                  .where((item) => item.isNotEmpty)
                  .join(' · '),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        onTap: () => _openCharacter(index: index),
        trailing: Wrap(
          spacing: 0,
          children: [
            IconButton(
              key: ValueKey('edit-character-$index'),
              tooltip: '编辑角色',
              onPressed: () => _openCharacter(index: index),
              icon: const Icon(Icons.edit_outlined),
            ),
            IconButton(
              key: ValueKey('remove-character-$index'),
              tooltip: '移除角色',
              onPressed: () => _removeCharacter(index),
              icon: const Icon(Icons.delete_outline),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionTitle(
    BuildContext context,
    String title,
    IconData icon, {
    String? subtitle,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                if (subtitle != null)
                  Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TemplateCharacterEditorPage extends StatefulWidget {
  const _TemplateCharacterEditorPage({
    required this.title,
    required this.initial,
  });

  final String title;
  final Map<String, dynamic> initial;

  @override
  State<_TemplateCharacterEditorPage> createState() =>
      _TemplateCharacterEditorPageState();
}

class _TemplateCharacterEditorPageState
    extends State<_TemplateCharacterEditorPage> {
  static const _fields = <_CharacterField>[
    _CharacterField('name', '姓名', required: true),
    _CharacterField('gender', '性别'),
    _CharacterField('age', '年龄'),
    _CharacterField('race_or_identity', '身份 / 种族'),
    _CharacterField('avatar_url', '专属头像地址'),
    _CharacterField('current_location', '开场位置'),
    _CharacterField('status', '开场状态'),
    _CharacterField('mood', '开场心情'),
    _CharacterField('relationship_to_player', '与玩家关系'),
    _CharacterField('relationship_score', '关系值', numeric: true),
    _CharacterField('affection_score', '好感值', numeric: true),
    _CharacterField('trust_score', '信任值', numeric: true),
    _CharacterField('tension_score', '张力值', numeric: true),
    _CharacterField('appearance', '外貌', lines: 3),
    _CharacterField('personality', '性格', lines: 3),
    _CharacterField('speech_style', '说话风格', lines: 3),
    _CharacterField('abilities', '能力', lines: 3),
    _CharacterField('current_goal', '当前目标', lines: 3),
    _CharacterField('hidden_goal', '隐藏目标', lines: 3),
    _CharacterField('memory_summary', '长期记忆', lines: 3),
  ];

  final Map<String, TextEditingController> _controllers = {};
  final List<_AttributeDraft> _attributes = [];
  late String _roleType;
  late bool _agentEnabled;
  late String _originalExtraAttributes;
  bool _attributesChanged = false;
  bool _attributeSourceUnreadable = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _roleType =
        widget.initial['role_type'] == 'protagonist' ? 'protagonist' : 'npc';
    _agentEnabled = widget.initial['agent_enabled'] is bool
        ? widget.initial['agent_enabled'] as bool
        : _roleType != 'protagonist';
    for (final field in _fields) {
      _controllers[field.key] = TextEditingController(
        text: widget.initial[field.key]?.toString() ?? '',
      );
    }
    _loadAttributes(widget.initial['extra_attrs']);
  }

  void _loadAttributes(dynamic source) {
    _originalExtraAttributes = source?.toString() ?? '{}';
    dynamic parsed = source;
    if (source is String && source.trim().isNotEmpty) {
      try {
        parsed = jsonDecode(source);
      } catch (_) {
        _attributeSourceUnreadable = true;
        return;
      }
    }
    if (parsed == null || parsed == '') return;
    if (parsed is! Map) {
      _attributeSourceUnreadable = true;
      return;
    }
    for (final entry in parsed.entries) {
      _attributes.add(_AttributeDraft(
        entry.key.toString(),
        entry.value is String ? entry.value as String : entry.value.toString(),
      ));
    }
  }

  void _addAttribute() {
    setState(() {
      _attributesChanged = true;
      _attributeSourceUnreadable = false;
      _attributes.add(_AttributeDraft('', ''));
    });
  }

  void _removeAttribute(int index) {
    setState(() {
      _attributesChanged = true;
      _attributes.removeAt(index).dispose();
    });
  }

  void _finish() {
    final name = _controllers['name']!.text.trim();
    if (name.isEmpty) {
      setState(() => _error = '请填写角色姓名。');
      return;
    }
    final data = <String, dynamic>{...widget.initial};
    for (final field in _fields) {
      final value = _controllers[field.key]!.text.trim();
      data[field.key] = field.numeric ? int.tryParse(value) ?? 0 : value;
    }
    data['role_type'] = _roleType;
    data['agent_enabled'] = _agentEnabled;
    if (_attributeSourceUnreadable && !_attributesChanged) {
      data['extra_attrs'] = _originalExtraAttributes;
    } else {
      data['extra_attrs'] = jsonEncode({
        for (final item in _attributes)
          if (item.key.text.trim().isNotEmpty)
            item.key.text.trim(): item.value.text.trim(),
      });
    }
    Navigator.pop(context, data);
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    for (final item in _attributes) {
      item.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title)),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
          children: [
            DropdownButtonFormField<String>(
              key: const ValueKey('character-role-type'),
              initialValue: _roleType,
              decoration: const InputDecoration(labelText: '角色类型'),
              items: const [
                DropdownMenuItem(value: 'protagonist', child: Text('主角')),
                DropdownMenuItem(value: 'npc', child: Text('NPC')),
              ],
              onChanged: (value) {
                if (value == null) return;
                setState(() {
                  _roleType = value;
                  if (value == 'protagonist') _agentEnabled = false;
                });
              },
            ),
            const SizedBox(height: 12),
            for (final field in _fields) ...[
              TextField(
                key: ValueKey('character-${field.key}'),
                controller: _controllers[field.key],
                maxLines: field.lines,
                keyboardType:
                    field.numeric ? TextInputType.number : TextInputType.text,
                decoration: InputDecoration(
                  labelText: '${field.label}${field.required ? ' *' : ''}',
                ),
              ),
              const SizedBox(height: 12),
            ],
            SwitchListTile(
              key: const ValueKey('character-agent-enabled'),
              contentPadding: const EdgeInsets.symmetric(horizontal: 4),
              title: const Text('启用 NPC 子智能体'),
              subtitle: const Text('关闭后该角色不会独立参与行为推演。'),
              value: _agentEnabled,
              onChanged: (value) => setState(() => _agentEnabled = value),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '扩展属性',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                TextButton.icon(
                  key: const ValueKey('add-character-attribute'),
                  onPressed: _addAttribute,
                  icon: const Icon(Icons.add),
                  label: const Text('添加属性'),
                ),
              ],
            ),
            if (_attributeSourceUnreadable)
              const Padding(
                padding: EdgeInsets.only(bottom: 10),
                child: Text('原扩展属性暂时无法展开，未修改时会保持原样。'),
              ),
            for (var index = 0; index < _attributes.length; index++)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        key: ValueKey('attribute-$index-key'),
                        controller: _attributes[index].key,
                        decoration: const InputDecoration(labelText: '属性名'),
                        onChanged: (_) => _attributesChanged = true,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        key: ValueKey('attribute-$index-value'),
                        controller: _attributes[index].value,
                        decoration: const InputDecoration(labelText: '属性值'),
                        onChanged: (_) => _attributesChanged = true,
                      ),
                    ),
                    IconButton(
                      key: ValueKey('remove-attribute-$index'),
                      onPressed: () => _removeAttribute(index),
                      icon: const Icon(Icons.remove_circle_outline),
                    ),
                  ],
                ),
              ),
            if (_error.isNotEmpty)
              Text(
                _error,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
        bottomNavigationBar: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            child: FilledButton.icon(
              key: const ValueKey('save-character'),
              onPressed: _finish,
              icon: const Icon(Icons.check),
              label: const Text('完成角色设计'),
            ),
          ),
        ),
      );
}

class _AttributeDraft {
  _AttributeDraft(String keyText, String valueText)
      : key = TextEditingController(text: keyText),
        value = TextEditingController(text: valueText);

  final TextEditingController key;
  final TextEditingController value;

  void dispose() {
    key.dispose();
    value.dispose();
  }
}

class _TemplateField {
  const _TemplateField(
    this.key,
    this.label, {
    this.lines = 1,
    this.required = false,
  });

  final String key;
  final String label;
  final int lines;
  final bool required;
}

class _CharacterField {
  const _CharacterField(
    this.key,
    this.label, {
    this.lines = 1,
    this.numeric = false,
    this.required = false,
  });

  final String key;
  final String label;
  final int lines;
  final bool numeric;
  final bool required;
}
