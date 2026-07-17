import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/ui/character_avatar.dart';
import '../../core/ui/record_form_page.dart';

class CharactersPage extends StatefulWidget {
  const CharactersPage({super.key, required this.api, required this.gameId});
  final ApiClient api;
  final int gameId;

  @override
  State<CharactersPage> createState() => _CharactersPageState();
}

class _CharactersPageState extends State<CharactersPage> {
  List<dynamic> _items = [];
  bool _loading = true;
  String _error = '';

  static const fields = [
    RecordField('name', '姓名', required: true, section: '基础资料'),
    RecordField('role_type', '角色类型', type: RecordFieldType.choice, options: {
      'protagonist': '主角',
      'npc': 'NPC',
      'supporting': '重要配角',
      'antagonist': '对手'
    }),
    RecordField('gender', '性别'),
    RecordField('age', '年龄'),
    RecordField('race_or_identity', '身份 / 种族'),
    RecordField('appearance', '外貌', lines: 3, section: '角色设定'),
    RecordField('personality', '性格', lines: 3),
    RecordField('speech_style', '说话风格', lines: 3),
    RecordField('abilities', '能力', lines: 3),
    RecordField('current_location', '当前位置', section: '当前状态'),
    RecordField('status', '状态', type: RecordFieldType.choice, options: {
      'normal': '正常',
      'injured': '受伤',
      'missing': '失踪',
      'dead': '死亡',
      'inactive': '离场'
    }),
    RecordField('mood', '心情'),
    RecordField('relationship_to_player', '与玩家关系', section: '关系数值'),
    RecordField('relationship_score', '关系值', type: RecordFieldType.integer),
    RecordField('affection_score', '好感度', type: RecordFieldType.integer),
    RecordField('trust_score', '信任度', type: RecordFieldType.integer),
    RecordField('tension_score', '张力', type: RecordFieldType.integer),
    RecordField('current_goal', '当前目标', lines: 3, section: '剧情与记忆'),
    RecordField('hidden_goal', '隐藏目标', lines: 3),
    RecordField('memory_summary', '记忆摘要', lines: 4),
    RecordField('agent_enabled', '启用 NPC 子 Agent',
        type: RecordFieldType.boolean,
        section: 'AI 与扩展',
        helper: '允许角色拥有独立记忆和行为倾向。'),
    RecordField('extra_attrs', '扩展属性 JSON', lines: 4),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = '';
      });
    }
    try {
      final value =
          await widget.api.getList('/games/${widget.gameId}/characters');
      if (mounted) setState(() => _items = value);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit([Map<String, dynamic>? item]) async {
    final changed = await Navigator.of(context).push<bool>(MaterialPageRoute(
        builder: (_) => RecordFormPage(
              title: item == null ? '新增角色' : '编辑角色',
              fields: fields,
              initial: item ??
                  const {
                    'role_type': 'npc',
                    'status': 'normal',
                    'agent_enabled': true,
                    'extra_attrs': '{}'
                  },
              onSave: (data) async {
                if (item == null) {
                  await widget.api
                      .postJson('/games/${widget.gameId}/characters', data);
                } else {
                  await widget.api.patchJson('/characters/${item['id']}', data);
                }
              },
              headerBuilder: (_, values) => DefaultAvatarPreview(
                character: values,
                avatarUrl: item == null
                    ? ''
                    : widget.api.mediaUrl(item['avatar_url']?.toString() ?? ''),
              ),
            )));
    if (changed == true) await _load();
  }

  Future<void> _avatar(Map<String, dynamic> item) async {
    try {
      final picked = await FilePicker.platform.pickFiles(type: FileType.image);
      final path = picked?.files.single.path;
      if (path == null) return;
      await widget.api.uploadFile('/characters/${item['id']}/avatar', path);
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  Future<void> _useAutomaticAvatar(Map<String, dynamic> item) async {
    if (await _confirm('移除“${item['name']}”的上传头像，恢复智能匹配？') != true) {
      return;
    }
    try {
      await widget.api.deleteJson('/characters/${item['id']}/avatar');
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  void _showAvatarLibrary() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .72,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('智能头像库',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text(
                      '创建角色时无需手动选择，系统会根据角色标签自动匹配。',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color:
                              Theme.of(context).colorScheme.onSurfaceVariant),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: GridView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    mainAxisSpacing: 10,
                    crossAxisSpacing: 10,
                    childAspectRatio: .82,
                  ),
                  itemCount: DefaultAvatarCatalog.profiles.length,
                  itemBuilder: (_, index) {
                    final profile = DefaultAvatarCatalog.profiles[index];
                    return Card(
                      clipBehavior: Clip.antiAlias,
                      child: Column(
                        children: [
                          Expanded(
                            child: Image.asset(profile.assetPath,
                                width: double.infinity, fit: BoxFit.cover),
                          ),
                          Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 4, vertical: 8),
                            child: Text(profile.label,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.labelMedium),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _delete(Map<String, dynamic> item) async {
    if (await _confirm('删除角色“${item['name']}”？') != true) return;
    try {
      await widget.api.deleteJson('/characters/${item['id']}');
      await _load();
    } catch (error) {
      _snack(error);
    }
  }

  Future<bool?> _confirm(String text) => showDialog<bool>(
      context: context,
      builder: (context) =>
          AlertDialog(title: const Text('确认删除'), content: Text(text), actions: [
            TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('取消')),
            FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('删除'))
          ]));
  void _snack(Object error) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
    }
  }

  String _roleLabel(Object? value) => switch (value?.toString()) {
        'protagonist' => '主角',
        'supporting' => '重要配角',
        'antagonist' => '对手',
        _ => 'NPC',
      };

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('角色管理'), actions: [
          IconButton(
              onPressed: _showAvatarLibrary,
              tooltip: '查看智能头像库',
              icon: const Icon(Icons.face_retouching_natural_outlined)),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh))
        ]),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? Center(child: Text(_error))
                : RefreshIndicator(
                    onRefresh: _load,
                    child: _items.isEmpty
                        ? ListView(
                            padding: const EdgeInsets.all(24),
                            children: const [Text('还没有角色，点击右下角新建。')])
                        : ListView.separated(
                            padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                            itemCount: _items.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 8),
                            itemBuilder: (_, index) {
                              final item =
                                  _items[index] as Map<String, dynamic>;
                              final avatar = widget.api.mediaUrl(
                                  item['avatar_url']?.toString() ?? '');
                              return Card(
                                  child: ListTile(
                                contentPadding:
                                    const EdgeInsets.fromLTRB(14, 10, 8, 10),
                                leading: CharacterAvatar(
                                  character: item,
                                  avatarUrl: avatar,
                                  size: 54,
                                  showAutoBadge: true,
                                ),
                                title: Text(item['name']?.toString() ?? '未命名'),
                                subtitle: Padding(
                                  padding: const EdgeInsets.only(top: 6),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Wrap(
                                          spacing: 6,
                                          runSpacing: 4,
                                          children: [
                                            _tag(_roleLabel(item['role_type'])),
                                            if (item['age']
                                                    ?.toString()
                                                    .trim()
                                                    .isNotEmpty ==
                                                true)
                                              _tag(item['age'].toString()),
                                            if (item['mood']
                                                    ?.toString()
                                                    .trim()
                                                    .isNotEmpty ==
                                                true)
                                              _tag(item['mood'].toString()),
                                          ]),
                                      const SizedBox(height: 6),
                                      Text(item['current_location']
                                                  ?.toString()
                                                  .trim()
                                                  .isNotEmpty ==
                                              true
                                          ? item['current_location'].toString()
                                          : '位置未设置'),
                                    ],
                                  ),
                                ),
                                onTap: () => _edit(item),
                                trailing: PopupMenuButton<String>(
                                    onSelected: (value) {
                                      if (value == 'avatar') _avatar(item);
                                      if (value == 'automatic') {
                                        _useAutomaticAvatar(item);
                                      }
                                      if (value == 'delete') _delete(item);
                                    },
                                    itemBuilder: (_) => [
                                          const PopupMenuItem(
                                              value: 'avatar',
                                              child: Text('上传头像')),
                                          if (avatar.isNotEmpty)
                                            const PopupMenuItem(
                                                value: 'automatic',
                                                child: Text('恢复智能头像')),
                                          const PopupMenuItem(
                                              value: 'delete',
                                              child: Text('删除'))
                                        ]),
                              ));
                            },
                          ),
                  ),
        floatingActionButton: FloatingActionButton(
            onPressed: _edit, child: const Icon(Icons.person_add_alt_1)),
      );

  Widget _tag(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(text, style: Theme.of(context).textTheme.labelSmall),
      );
}
