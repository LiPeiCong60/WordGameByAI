import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../admin/admin_page.dart';
import '../templates/templates_page.dart';
import 'game_form_page.dart';
import 'game_workspace_page.dart';

class GameListPage extends StatefulWidget {
  const GameListPage(
      {super.key,
      required this.api,
      required this.user,
      required this.onLogout});

  final ApiClient api;
  final Map<String, dynamic> user;
  final Future<void> Function() onLogout;

  @override
  State<GameListPage> createState() => _GameListPageState();
}

class _GameListPageState extends State<GameListPage> {
  List<dynamic> _games = [];
  bool _loading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = '';
      });
    }
    try {
      final games = await widget.api.getList('/games');
      if (mounted) setState(() => _games = games);
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(error));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _create() async {
    final game = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(builder: (_) => GameFormPage(api: widget.api)),
    );
    if (game == null || !mounted) return;
    await _reload();
    if (!mounted) return;
    await _openGame(game);
  }

  Future<void> _openGame(Map<String, dynamic> game) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
          builder: (_) => GameWorkspacePage(api: widget.api, game: game)),
    );
    await _reload();
  }

  Future<void> _delete(Map<String, dynamic> game) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除存档'),
        content: Text('确定彻底删除“${game['title']}”吗？角色、世界、设定和剧情记录也会被删除。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('删除')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.deleteJson('/games/${game['id']}');
      await _reload();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _export(Map<String, dynamic> game) async {
    try {
      final data = await widget.api.getJson('/games/${game['id']}/export');
      final bytes = Uint8List.fromList(
          utf8.encode(const JsonEncoder.withIndent('  ').convert(data)));
      await FilePicker.platform.saveFile(
        dialogTitle: '导出存档',
        fileName: 'world-game-${game['id']}.json',
        type: FileType.custom,
        allowedExtensions: const ['json'],
        bytes: bytes,
      );
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('存档已导出。')));
      }
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _import() async {
    try {
      final result = await FilePicker.platform.pickFiles(
          type: FileType.custom,
          allowedExtensions: const ['json'],
          withData: true);
      final bytes = result?.files.single.bytes;
      if (bytes == null) return;
      final payload = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
      final imported = await widget.api.postJson('/games/import', payload);
      await _reload();
      final game = imported['game'];
      if (game is Map<String, dynamic> && mounted) await _openGame(game);
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(apiErrorMessage(error))));
  }

  void _openTemplates() {
    Navigator.of(context).push<void>(MaterialPageRoute(
        builder: (_) => TemplatesPage(api: widget.api, user: widget.user)));
  }

  void _openAdmin() {
    Navigator.of(context).push<void>(
        MaterialPageRoute(builder: (_) => AdminPage(api: widget.api)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child:
                Image.asset('assets/brand/app_icon.png', width: 34, height: 34),
          ),
          const SizedBox(width: 10),
          const Text('World Game by AI'),
        ]),
        actions: [
          IconButton(
              onPressed: _import,
              tooltip: '导入存档',
              icon: const Icon(Icons.upload_file_outlined)),
          IconButton(
              onPressed: _reload,
              tooltip: '刷新',
              icon: const Icon(Icons.refresh)),
        ],
      ),
      drawer: NavigationDrawer(
        header: Padding(
          padding: const EdgeInsets.fromLTRB(28, 28, 20, 16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Image.asset('assets/brand/app_icon.png',
                  width: 52, height: 52),
            ),
            const SizedBox(height: 12),
            Text(widget.user['username']?.toString() ?? '用户',
                style: Theme.of(context).textTheme.titleLarge),
            Text(widget.user['is_admin'] == true
                ? '管理员'
                : (widget.user['is_member'] == true ? '会员' : '普通用户')),
          ]),
        ),
        children: [
          const NavigationDrawerDestination(
              icon: Icon(Icons.save_outlined),
              selectedIcon: Icon(Icons.save),
              label: Text('我的存档')),
          ListTile(
              leading: const Icon(Icons.dashboard_customize_outlined),
              title: const Text('世界模板'),
              onTap: _openTemplates),
          if (widget.user['is_admin'] == true)
            ListTile(
                leading: const Icon(Icons.admin_panel_settings_outlined),
                title: const Text('管理员中心'),
                onTap: _openAdmin),
          const Divider(),
          ListTile(
              leading: const Icon(Icons.logout),
              title: const Text('退出登录'),
              onTap: widget.onLogout),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? ListView(children: [
                    ListTile(
                        leading: const Icon(Icons.error_outline),
                        title: Text(_error),
                        trailing: TextButton(
                            onPressed: _reload, child: const Text('重试')))
                  ])
                : _games.isEmpty
                    ? ListView(padding: const EdgeInsets.all(24), children: [
                        const SizedBox(height: 80),
                        Center(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(24),
                            child: Image.asset('assets/brand/app_icon.png',
                                width: 92, height: 92),
                          ),
                        ),
                        const SizedBox(height: 20),
                        Text('还没有存档',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        const Text('直接在 App 里创建第一个世界，不需要打开网页。',
                            textAlign: TextAlign.center),
                        const SizedBox(height: 24),
                        FilledButton.icon(
                            onPressed: _create,
                            icon: const Icon(Icons.add),
                            label: const Text('创建存档')),
                      ])
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                        itemCount: _games.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          final game = _games[index] as Map<String, dynamic>;
                          return Card(
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () => _openGame(game),
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Row(children: [
                                  CircleAvatar(
                                      child: Text((game['title']
                                              ?.toString()
                                              .characters
                                              .firstOrNull ??
                                          '游'))),
                                  const SizedBox(width: 14),
                                  Expanded(
                                      child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                        Text(
                                            game['title']?.toString() ??
                                                '未命名存档',
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium),
                                        const SizedBox(height: 4),
                                        Text(
                                            '${game['genre']?.toString().isNotEmpty == true ? game['genre'] : '未设置题材'} · ${game['world_type']?.toString().isNotEmpty == true ? game['world_type'] : '未设置世界'}'),
                                      ])),
                                  PopupMenuButton<String>(
                                    onSelected: (value) {
                                      if (value == 'export') _export(game);
                                      if (value == 'delete') _delete(game);
                                    },
                                    itemBuilder: (_) => const [
                                      PopupMenuItem(
                                          value: 'export',
                                          child: ListTile(
                                              leading:
                                                  Icon(Icons.download_outlined),
                                              title: Text('导出'),
                                              contentPadding: EdgeInsets.zero)),
                                      PopupMenuItem(
                                          value: 'delete',
                                          child: ListTile(
                                              leading:
                                                  Icon(Icons.delete_outline),
                                              title: Text('删除'),
                                              contentPadding: EdgeInsets.zero)),
                                    ],
                                  ),
                                ]),
                              ),
                            ),
                          );
                        },
                      ),
      ),
      floatingActionButton: FloatingActionButton.extended(
          onPressed: _create,
          icon: const Icon(Icons.add),
          label: const Text('新建存档')),
    );
  }
}
