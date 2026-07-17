import 'dart:convert';

import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/ui/record_form_page.dart';

class AdminPage extends StatefulWidget {
  const AdminPage({super.key, required this.api});
  final ApiClient api;
  @override
  State<AdminPage> createState() => _AdminPageState();
}

class _AdminPageState extends State<AdminPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 4, vsync: this);
  Map<String, dynamic> _summary = {};
  Map<String, dynamic> _config = {
    'models': [],
    'levels': [],
    'agent_names': []
  };
  List<dynamic> _users = [], _games = [], _usage = [];
  bool _loading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = '';
    });
    try {
      final values = await Future.wait([
        widget.api.getJson('/admin/summary'),
        widget.api.getList('/admin/users'),
        widget.api.getList('/admin/games'),
        widget.api.getJson('/admin/model-config'),
        widget.api.getList('/admin/token-usage/summary')
      ]);
      if (mounted) {
        setState(() {
          _summary = values[0] as Map<String, dynamic>;
          _users = values[1] as List<dynamic>;
          _games = values[2] as List<dynamic>;
          _config = values[3] as Map<String, dynamic>;
          _usage = values[4] as List<dynamic>;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<dynamic> get _models => _config['models'] as List<dynamic>? ?? [];
  List<dynamic> get _levels => _config['levels'] as List<dynamic>? ?? [];

  Future<void> _editUser(Map<String, dynamic> user) async {
    bool active = user['is_active'] == true,
        admin = user['is_admin'] == true,
        member = user['is_member'] == true;
    String level = user['model_level_id']?.toString() ?? '';
    final quota = TextEditingController(
        text: user['daily_message_limit']?.toString() ?? '20');
    final result = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (c) => StatefulBuilder(
            builder: (c, setLocal) => AlertDialog(
                  title: Text('用户：${user['username']}'),
                  scrollable: true,
                  content: Column(mainAxisSize: MainAxisSize.min, children: [
                    SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('账号启用'),
                        value: active,
                        onChanged: (v) => setLocal(() => active = v)),
                    SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('管理员'),
                        value: admin,
                        onChanged: (v) => setLocal(() => admin = v)),
                    SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('会员'),
                        value: member,
                        onChanged: (v) => setLocal(() => member = v)),
                    TextField(
                        controller: quota,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: '每日消息上限')),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                        initialValue: level,
                        decoration: const InputDecoration(labelText: '模型等级'),
                        items: [
                          const DropdownMenuItem(
                              value: '', child: Text('默认等级')),
                          ..._levels.map((v) => DropdownMenuItem(
                              value: v['id']?.toString() ?? '',
                              child: Text(v['label']?.toString() ??
                                  v['id'].toString())))
                        ],
                        onChanged: (v) => setLocal(() => level = v ?? '')),
                  ]),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(c),
                        child: const Text('取消')),
                    FilledButton(
                        onPressed: () => Navigator.pop(c, {
                              'is_active': active,
                              'is_admin': admin,
                              'is_member': member,
                              'daily_message_limit':
                                  int.tryParse(quota.text) ?? 20,
                              'level_id': level
                            }),
                        child: const Text('保存'))
                  ],
                )));
    quota.dispose();
    if (result == null) return;
    try {
      final levelId = result.remove('level_id') as String;
      await widget.api.patchJson('/admin/users/${user['id']}', result);
      await widget.api.patchJson(
          '/admin/users/${user['id']}/model-level', {'level_id': levelId});
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _userUsage(Map<String, dynamic> user) async {
    try {
      final usage =
          await widget.api.getList('/admin/users/${user['id']}/token-usage');
      if (!mounted) return;
      _showJson('${user['username']} 的 Token 消耗', usage);
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _editModel([Map<String, dynamic>? model]) async {
    final changed = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => RecordFormPage(
                title: model == null ? '新增模型' : '编辑模型',
                initial: model ?? const {'temperature': 0.7, 'enabled': true},
                fields: const [
                  RecordField('id', '配置 ID', required: true),
                  RecordField('label', '显示名称'),
                  RecordField('base_url', 'Base URL'),
                  RecordField('model', '模型名'),
                  RecordField('temperature', 'Temperature',
                      type: RecordFieldType.decimal),
                  RecordField('api_key', 'API Key（留空保留原密钥）',
                      type: RecordFieldType.password),
                  RecordField('enabled', '启用', type: RecordFieldType.boolean),
                  RecordField('clear_api_key', '清除已保存密钥',
                      type: RecordFieldType.boolean)
                ],
                onSave: (data) async {
                  await widget.api.putJson('/admin/model-config/models', data);
                })));
    if (changed == true) await _load();
  }

  Future<void> _editLevel([Map<String, dynamic>? level]) async {
    final initial = level == null
        ? <String, dynamic>{'agent_models': '{}'}
        : {
            ...level,
            'agent_models': const JsonEncoder.withIndent('  ')
                .convert(level['agent_models'] ?? {})
          };
    final changed = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => RecordFormPage(
                title: level == null ? '新增模型等级' : '编辑模型等级',
                initial: initial,
                fields: const [
                  RecordField('id', '等级 ID', required: true),
                  RecordField('label', '等级名称'),
                  RecordField('description', '说明', lines: 3),
                  RecordField('fallback_model_id', '兜底模型 ID'),
                  RecordField('agent_models', 'Agent 模型分配 JSON', lines: 10)
                ],
                onSave: (data) async {
                  final raw = data['agent_models']?.toString() ?? '{}';
                  data['agent_models'] =
                      jsonDecode(raw) as Map<String, dynamic>;
                  await widget.api.putJson('/admin/model-config/levels', data);
                })));
    if (changed == true) await _load();
  }

  Future<void> _defaultModel(String id) async {
    try {
      await widget.api
          .patchJson('/admin/model-config/default-model', {'model_id': id});
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _defaultLevel(String id) async {
    try {
      await widget.api
          .patchJson('/admin/model-config/default-level', {'level_id': id});
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _deleteModel(String id) async {
    try {
      await widget.api.deleteJson('/admin/model-config/models/$id');
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  Future<void> _deleteLevel(String id) async {
    try {
      await widget.api.deleteJson('/admin/model-config/levels/$id');
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

  void _showJson(String title, Object data) {
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

  Widget _stat(String label, Object? value, IconData icon) => Card(
      child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(children: [
            Icon(icon),
            const SizedBox(width: 12),
            Expanded(child: Text(label)),
            Text('${value ?? '-'}',
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 20))
          ])));

  Widget _overviewTab() => ListView(
        padding: const EdgeInsets.all(12),
        children: [
          GridView.count(
            crossAxisCount: 2,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: 2.3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              _stat('用户', _summary['users'], Icons.people),
              _stat('存档', _summary['games'], Icons.save),
              _stat('回合', _summary['turns'], Icons.forum),
              _stat(
                  '待确认', _summary['pending_proposals'], Icons.pending_actions),
            ],
          ),
          const SizedBox(height: 16),
          Text('全局 Token 消耗', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          ..._usage.map((item) => Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(item['model_name']?.toString() ?? '未知模型'),
                  subtitle: Text(
                      '提示 ${item['prompt_tokens'] ?? 0} · 生成 ${item['completion_tokens'] ?? 0}'),
                  trailing: Text('${item['total_tokens'] ?? 0}'),
                ),
              )),
        ],
      );

  Widget _usersTab() => ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _users.length,
        itemBuilder: (_, index) {
          final user = _users[index] as Map<String, dynamic>;
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: CircleAvatar(
                  child: Text(
                      user['username']?.toString().characters.firstOrNull ??
                          '?')),
              title: Text(user['username']?.toString() ?? '用户'),
              subtitle: Text(
                '${user['is_admin'] == true ? '管理员' : '玩家'} · ${user['is_member'] == true ? '会员' : '非会员'} · ${user['is_active'] == true ? '启用' : '停用'}\n'
                '今日 ${user['today_message_count'] ?? 0}/${user['effective_daily_message_limit'] ?? '-'} · Token ${user['total_tokens'] ?? 0}',
              ),
              isThreeLine: true,
              onTap: () => _userUsage(user),
              trailing: IconButton(
                  onPressed: () => _editUser(user),
                  icon: const Icon(Icons.edit_outlined)),
            ),
          );
        },
      );

  Widget _modelsTab() => ListView(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
        children: [
          Row(children: [
            Expanded(
                child:
                    Text('模型池', style: Theme.of(context).textTheme.titleLarge)),
            FilledButton.tonalIcon(
                onPressed: _editModel,
                icon: const Icon(Icons.add),
                label: const Text('模型'))
          ]),
          const SizedBox(height: 8),
          ..._models.map((raw) {
            final model = raw as Map<String, dynamic>;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title:
                    Text(model['label']?.toString() ?? model['id'].toString()),
                subtitle: Text(
                    '${model['model'] ?? '-'}\n${model['base_url'] ?? '-'}'),
                isThreeLine: true,
                leading: Icon(model['id'] == _config['default_model_id']
                    ? Icons.star
                    : Icons.memory),
                onTap: () => _editModel(model),
                trailing: PopupMenuButton<String>(
                  onSelected: (value) {
                    if (value == 'default') {
                      _defaultModel(model['id'].toString());
                    }
                    if (value == 'delete') _deleteModel(model['id'].toString());
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'default', child: Text('设为全局兜底')),
                    PopupMenuItem(value: 'delete', child: Text('删除'))
                  ],
                ),
              ),
            );
          }),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(
                child: Text('模型等级 / Agent 分配',
                    style: Theme.of(context).textTheme.titleLarge)),
            FilledButton.tonalIcon(
                onPressed: _editLevel,
                icon: const Icon(Icons.add),
                label: const Text('等级'))
          ]),
          const SizedBox(height: 8),
          ..._levels.map((raw) {
            final level = raw as Map<String, dynamic>;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title:
                    Text(level['label']?.toString() ?? level['id'].toString()),
                subtitle: Text(
                    '${level['description'] ?? ''}\n兜底：${level['fallback_model_id'] ?? '全局'}'),
                isThreeLine: true,
                leading: Icon(level['id'] == _config['default_level_id']
                    ? Icons.star
                    : Icons.layers),
                onTap: () => _editLevel(level),
                trailing: PopupMenuButton<String>(
                  onSelected: (value) {
                    if (value == 'default') {
                      _defaultLevel(level['id'].toString());
                    }
                    if (value == 'delete') _deleteLevel(level['id'].toString());
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'default', child: Text('设为默认等级')),
                    PopupMenuItem(value: 'delete', child: Text('删除'))
                  ],
                ),
              ),
            );
          }),
        ],
      );

  Widget _gamesTab() => ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _games.length,
        itemBuilder: (_, index) {
          final game = _games[index];
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: const Icon(Icons.save_outlined),
              title: Text(game['title']?.toString() ?? '未命名'),
              subtitle: Text(
                  '${game['genre'] ?? '未设置题材'} · 所有者 ${game['owner_username'] ?? '未归属'}'),
              trailing: Text('#${game['id']}'),
            ),
          );
        },
      );

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('管理员中心'),
          actions: [
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh))
          ],
          bottom: TabBar(controller: _tabs, isScrollable: true, tabs: const [
            Tab(text: '概览'),
            Tab(text: '用户'),
            Tab(text: '模型配置'),
            Tab(text: '全部存档')
          ]),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? Center(child: Text(_error))
                : TabBarView(controller: _tabs, children: [
                    _overviewTab(),
                    _usersTab(),
                    _modelsTab(),
                    _gamesTab()
                  ]),
      );
}
