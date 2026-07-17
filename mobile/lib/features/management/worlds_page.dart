import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/ui/record_form_page.dart';

class WorldsPage extends StatefulWidget {
  const WorldsPage({super.key, required this.api, required this.gameId});
  final ApiClient api;
  final int gameId;
  @override
  State<WorldsPage> createState() => _WorldsPageState();
}

class _WorldsPageState extends State<WorldsPage> {
  List<dynamic> _items = [];
  Map<String, dynamic> _game = {};
  bool _loading = true;
  String _error = '';
  static const fields = [
    RecordField('name', '名称', required: true),
    RecordField('world_type', '世界类型'),
    RecordField('summary', '摘要', lines: 4),
    RecordField('current_status', '当前状态', lines: 4),
    RecordField('mission_objective', '任务目标', lines: 3),
    RecordField('completion_condition', '完成条件', lines: 2),
    RecordField('failure_condition', '失败条件', lines: 2),
    RecordField('plot_deviation', '剧情偏移度', type: RecordFieldType.integer),
  ];
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final values = await Future.wait([
        widget.api.getList('/games/${widget.gameId}/story-worlds'),
        widget.api.getJson('/games/${widget.gameId}')
      ]);
      if (mounted) {
        setState(() {
          _items = values[0] as List<dynamic>;
          _game = values[1] as Map<String, dynamic>;
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
                title: item == null ? '新增世界' : '编辑世界',
                fields: fields,
                initial: item ?? const {'plot_deviation': 0},
                onSave: (data) async {
                  if (item == null) {
                    await widget.api
                        .postJson('/games/${widget.gameId}/story-worlds', data);
                  } else {
                    await widget.api
                        .patchJson('/story-worlds/${item['id']}', data);
                  }
                })));
    if (changed == true) await _load();
  }

  Future<void> _current(int id) async {
    try {
      await widget.api
          .postJson('/games/${widget.gameId}/story-worlds/$id/set-current');
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _delete(int id) async {
    if (await showDialog<bool>(
            context: context,
            builder: (c) => AlertDialog(
                    title: const Text('删除世界'),
                    content: const Text('确定删除这个世界？'),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(c, false),
                          child: const Text('取消')),
                      FilledButton(
                          onPressed: () => Navigator.pop(c, true),
                          child: const Text('删除'))
                    ])) !=
        true) {
      return;
    }
    try {
      await widget.api.deleteJson('/story-worlds/$id');
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
        appBar: AppBar(
          title: const Text('世界 / 副本'),
          actions: [
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh))
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? Center(child: Text(_error))
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                    itemCount: _items.length,
                    itemBuilder: (_, i) {
                      final item = _items[i] as Map<String, dynamic>;
                      final current =
                          item['id'] == _game['current_story_world_id'];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: Icon(
                              current ? Icons.flag : Icons.public_outlined),
                          title: Text(item['name']?.toString() ?? '未命名'),
                          subtitle: Text(
                              '${item['world_type'] ?? ''}\n${item['mission_objective'] ?? item['summary'] ?? ''}'),
                          isThreeLine: true,
                          onTap: () => _edit(item),
                          trailing: PopupMenuButton<String>(
                            onSelected: (value) {
                              if (value == 'current') {
                                _current(item['id'] as int);
                              }
                              if (value == 'delete') _delete(item['id'] as int);
                            },
                            itemBuilder: (_) => [
                              if (!current)
                                const PopupMenuItem(
                                    value: 'current', child: Text('设为当前世界')),
                              const PopupMenuItem(
                                  value: 'delete', child: Text('删除')),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
        floatingActionButton: FloatingActionButton(
            onPressed: _edit, child: const Icon(Icons.add)),
      );
}
