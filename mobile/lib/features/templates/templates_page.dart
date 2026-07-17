import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/ui/record_form_page.dart';
import '../management/game_agent_page.dart';

class TemplatesPage extends StatefulWidget {
  const TemplatesPage({super.key, required this.api, required this.user});
  final ApiClient api;
  final Map<String, dynamic> user;
  @override
  State<TemplatesPage> createState() => _TemplatesPageState();
}

class _TemplatesPageState extends State<TemplatesPage> {
  List<dynamic> _items = [];
  bool _loading = true;
  String _error = '';
  List<RecordField> get _fields => [
        const RecordField('name', '名称', required: true),
        const RecordField('genre', '题材'),
        const RecordField('world_type', '世界类型'),
        const RecordField('tone', '基调'),
        if (widget.user['is_admin'] == true)
          const RecordField('is_public', '公开模板', type: RecordFieldType.boolean),
        const RecordField('description', '模板描述', lines: 3),
        const RecordField('default_style_guide', '默认文风', lines: 5),
        const RecordField('default_rules', '默认世界规则', lines: 5),
        const RecordField('default_character_fields', '开局角色设计 JSON',
            lines: 12, helper: '支持 characters 数组，可定义主角和 NPC 的全部字段。'),
      ];
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final items = await widget.api.getList('/templates');
      if (mounted) {
        setState(() {
          _items = items;
          _error = '';
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  bool _canEdit(Map<String, dynamic> item) =>
      widget.user['is_admin'] == true ||
      item['owner_user_id'] == widget.user['id'];
  Future<void> _edit([Map<String, dynamic>? source]) async {
    final editable = source == null || _canEdit(source);
    final item = source == null
        ? null
        : editable
            ? source
            : {
                ...source,
                'id': null,
                'name': '${source['name']} 副本',
                'is_public': false
              };
    final initial = item == null
        ? const <String, dynamic>{
            'default_character_fields': '{\n  "characters": []\n}'
          }
        : {...item, 'is_public': item['owner_user_id'] == null};
    final changed = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => RecordFormPage(
                title: item?['id'] == null ? '新增模板' : '编辑模板',
                fields: _fields,
                initial: initial,
                onSave: (data) async {
                  if (item?['id'] == null) {
                    await widget.api.postJson('/templates', data);
                  } else {
                    await widget.api
                        .patchJson('/templates/${item!['id']}', data);
                  }
                })));
    if (changed == true) await _load();
  }

  Future<void> _delete(Map<String, dynamic> item) async {
    if (!_canEdit(item)) return;
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
                title: const Text('删除模板'),
                content: Text('确定删除“${item['name']}”？'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c, false),
                      child: const Text('取消')),
                  FilledButton(
                      onPressed: () => Navigator.pop(c, true),
                      child: const Text('删除'))
                ]));
    if (ok != true) return;
    try {
      await widget.api.deleteJson('/templates/${item['id']}');
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  void _snack(Object e) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('世界模板'), actions: [
          IconButton(
              onPressed: () => Navigator.push<void>(
                  context,
                  MaterialPageRoute(
                      builder: (_) =>
                          GameAgentPage(api: widget.api, gameId: 0))),
              tooltip: '模板智能助手',
              icon: const Icon(Icons.smart_toy_outlined)),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh))
        ]),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? Center(child: Text(_error))
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                    itemCount: _items.length,
                    itemBuilder: (_, i) {
                      final item = _items[i] as Map<String, dynamic>;
                      final own = _canEdit(item);
                      final public = item['owner_user_id'] == null;
                      return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                              leading: Icon(
                                  public ? Icons.public : Icons.lock_outline),
                              title: Text(item['name']?.toString() ?? '未命名'),
                              subtitle: Text(
                                  '${public ? '公共模板' : '我的模板'} · ${item['genre'] ?? ''} · ${item['world_type'] ?? ''}\n${item['description'] ?? item['default_rules'] ?? ''}',
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis),
                              isThreeLine: true,
                              onTap: () => _edit(item),
                              trailing: PopupMenuButton<String>(
                                  onSelected: (v) {
                                    if (v == 'edit') _edit(item);
                                    if (v == 'delete') _delete(item);
                                  },
                                  itemBuilder: (_) => [
                                        PopupMenuItem(
                                            value: 'edit',
                                            child:
                                                Text(own ? '编辑' : '复制为我的模板')),
                                        if (own)
                                          const PopupMenuItem(
                                              value: 'delete',
                                              child: Text('删除'))
                                      ])));
                    }),
        floatingActionButton: FloatingActionButton.extended(
            onPressed: _edit,
            icon: const Icon(Icons.add),
            label: const Text('新建模板')),
      );
}
