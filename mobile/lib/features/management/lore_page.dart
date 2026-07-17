import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/ui/record_form_page.dart';

class LorePage extends StatefulWidget {
  const LorePage({super.key, required this.api, required this.gameId});
  final ApiClient api;
  final int gameId;
  @override
  State<LorePage> createState() => _LorePageState();
}

class _LorePageState extends State<LorePage> {
  List<dynamic> _items = [];
  bool _loading = true;
  String _error = '';
  static const fields = [
    RecordField('title', '标题', required: true),
    RecordField('category', '分类'),
    RecordField('canon_level', '权威等级', type: RecordFieldType.choice, options: {
      'hard_canon': '硬性设定',
      'soft_canon': '软性设定',
      'rumor': '传闻',
      'secret': '秘密'
    }),
    RecordField('importance', '重要度（1-10）', type: RecordFieldType.integer),
    RecordField('content', '内容', lines: 8),
  ];
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final items = await widget.api.getList('/games/${widget.gameId}/lore');
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

  Future<void> _edit([Map<String, dynamic>? item]) async {
    final changed = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => RecordFormPage(
                title: item == null ? '新增设定' : '编辑设定',
                fields: fields,
                initial: item ??
                    const {
                      'category': '其他',
                      'canon_level': 'soft_canon',
                      'importance': 5
                    },
                onSave: (data) async {
                  if (item == null) {
                    await widget.api
                        .postJson('/games/${widget.gameId}/lore', data);
                  } else {
                    await widget.api.patchJson('/lore/${item['id']}', data);
                  }
                })));
    if (changed == true) await _load();
  }

  Future<void> _organize() async {
    final controller = TextEditingController();
    final text = await showDialog<String>(
        context: context,
        builder: (c) => AlertDialog(
                title: const Text('LoreAgent 智能整理'),
                content: TextField(
                    controller: controller,
                    maxLines: 8,
                    decoration: const InputDecoration(hintText: '粘贴零散的世界观设定…')),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c),
                      child: const Text('取消')),
                  FilledButton(
                      onPressed: () => Navigator.pop(c, controller.text.trim()),
                      child: const Text('整理'))
                ]));
    controller.dispose();
    if (text == null || text.isEmpty) return;
    try {
      final result = await widget.api
          .postJson('/games/${widget.gameId}/lore/organize', {'text': text});
      if (!mounted) return;
      await _edit({
        ...result,
        'importance': result['importance'] ?? 5,
        'canon_level': result['canon_level'] ?? 'soft_canon'
      });
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _delete(int id) async {
    try {
      await widget.api.deleteJson('/lore/$id');
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
      appBar: AppBar(title: const Text('世界观设定'), actions: [
        IconButton(
            onPressed: _organize,
            tooltip: '智能整理',
            icon: const Icon(Icons.auto_awesome)),
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
                    return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                            title: Text(item['title']?.toString() ?? '未命名'),
                            subtitle: Text(
                                '${item['category'] ?? '其他'} · 重要度 ${item['importance'] ?? 5}\n${item['content'] ?? ''}',
                                maxLines: 4,
                                overflow: TextOverflow.ellipsis),
                            isThreeLine: true,
                            onTap: () => _edit(item),
                            trailing: IconButton(
                                onPressed: () => _delete(item['id'] as int),
                                icon: const Icon(Icons.delete_outline))));
                  }),
      floatingActionButton:
          FloatingActionButton(onPressed: _edit, child: const Icon(Icons.add)));
}
