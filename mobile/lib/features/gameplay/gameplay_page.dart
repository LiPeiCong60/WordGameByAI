import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../core/config/app_config.dart';
import '../../core/network/api_client.dart';
import '../../core/ui/character_avatar.dart';
import 'story_parser.dart';

class GameplayPage extends StatefulWidget {
  const GameplayPage({super.key, required this.api, required this.gameId});
  final ApiClient api;
  final int gameId;
  @override
  State<GameplayPage> createState() => _GameplayPageState();
}

class _GameplayPageState extends State<GameplayPage> {
  final _action = TextEditingController(), _dialogue = TextEditingController();
  final _scroll = ScrollController();
  final List<Map<String, dynamic>> _turns = [], _characters = [];
  Map<String, dynamic> _game = {}, _world = {};
  String _title = '剧情', _streamingText = '', _status = '', _mode = 'fast';
  bool _loading = true,
      _generating = false,
      _legacyApi = false,
      _autoComplete = true,
      _hasMore = false;
  int? _nextCursor;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await widget.api.getJson(
          AppConfig.v1Path('/games/${widget.gameId}/bootstrap'),
          query: {'turn_limit': 30});
      if (!mounted) return;
      final game = (data['game'] as Map?)?.cast<String, dynamic>() ?? {};
      final turns = (data['turns'] as Map?)?.cast<String, dynamic>() ?? {};
      setState(() {
        _legacyApi = false;
        _game = game;
        _world = (data['current_world'] as Map?)?.cast<String, dynamic>() ?? {};
        _title = game['title']?.toString() ?? '剧情';
        _turns
          ..clear()
          ..addAll(((turns['items'] as List?) ?? [])
              .map((e) => (e as Map).cast<String, dynamic>()));
        _characters
          ..clear()
          ..addAll(((data['characters'] as List?) ?? [])
              .map((e) => (e as Map).cast<String, dynamic>()));
        _hasMore = turns['has_more'] == true;
        _nextCursor = turns['next_cursor'] as int?;
        _loading = false;
        _status = '';
      });
      _scrollToBottom();
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        await _loadLegacy();
        return;
      }
      _loadFailed(error);
    } catch (error) {
      _loadFailed(error);
    }
  }

  Future<void> _loadLegacy() async {
    try {
      final values = await Future.wait([
        widget.api.getJson('/games/${widget.gameId}'),
        widget.api.getList('/games/${widget.gameId}/characters'),
        widget.api.getList('/games/${widget.gameId}/story-worlds'),
        widget.api.getJson('/games/${widget.gameId}/export'),
      ]);
      if (!mounted) return;
      final game = values[0] as Map<String, dynamic>;
      final worlds = values[2] as List<dynamic>;
      final save = values[3] as Map<String, dynamic>;
      final turns = (save['turn_logs'] as List<dynamic>? ?? [])
          .map((item) => (item as Map).cast<String, dynamic>())
          .toList()
        ..sort((left, right) => ((left['turn_number'] as num?) ?? 0)
            .compareTo((right['turn_number'] as num?) ?? 0));
      setState(() {
        _legacyApi = true;
        _game = game;
        _title = game['title']?.toString() ?? '剧情';
        _characters
          ..clear()
          ..addAll((values[1] as List<dynamic>)
              .map((e) => (e as Map).cast<String, dynamic>()));
        _turns
          ..clear()
          ..addAll(turns);
        _world = worlds
                .cast<Map<String, dynamic>>()
                .where((w) => w['id'] == game['current_story_world_id'])
                .firstOrNull ??
            (worlds.isEmpty
                ? {}
                : (worlds.first as Map).cast<String, dynamic>());
        _loading = false;
      });
    } catch (error) {
      _loadFailed(error);
    }
  }

  Future<void> _loadOlder() async {
    if (_legacyApi || !_hasMore || _nextCursor == null) return;
    try {
      final page = await widget.api.getJson(
          AppConfig.v1Path('/games/${widget.gameId}/turns'),
          query: {'limit': 30, 'before_id': _nextCursor});
      final older = ((page['items'] as List?) ?? [])
          .map((e) => (e as Map).cast<String, dynamic>());
      if (mounted) {
        setState(() {
          _turns.insertAll(0, older);
          _hasMore = page['has_more'] == true;
          _nextCursor = page['next_cursor'] as int?;
        });
      }
    } catch (e) {
      _snack(e);
    }
  }

  void _loadFailed(Object error) {
    if (mounted) {
      setState(() {
        _loading = false;
        _status = '加载失败：${apiErrorMessage(error)}';
      });
    }
  }

  Future<void> _opening() async {
    if (_generating) return;
    await _runStream(
        widget.api.postNdjson('/games/${widget.gameId}/opening/stream', null,
            headers: {'X-Request-ID': const Uuid().v4()}),
        opening: true);
  }

  Future<void> _submit() async {
    if (_generating ||
        (_action.text.trim().isEmpty && _dialogue.text.trim().isEmpty)) {
      return;
    }
    final payload = {
      'request_id': const Uuid().v4(),
      'action_input': _action.text.trim(),
      'dialogue_input': _dialogue.text.trim(),
      'auto_complete_blank': _autoComplete,
      'fast_mode': _mode != 'full',
      'skip_state_update': _mode == 'instant',
      'async_state_update': _mode == 'fast'
    };
    await _runStream(
        widget.api.postNdjson('/games/${widget.gameId}/turn/stream', payload));
    if (!_generating) {
      _action.clear();
      _dialogue.clear();
    }
  }

  Future<void> _runStream(Stream<Map<String, dynamic>> events,
      {bool opening = false}) async {
    setState(() {
      _generating = true;
      _streamingText = '';
      _status = opening ? '正在生成开场…' : '正在连接模型…';
    });
    Map<String, dynamic>? done;
    try {
      await for (final event in events) {
        if (!mounted) return;
        setState(() {
          if (event['type'] == 'status') {
            _status = event['message']?.toString() ?? '';
          }
          if (event['type'] == 'delta') {
            _streamingText += event['text']?.toString() ?? '';
          }
          if (event['type'] == 'done') {
            done = event;
            _status =
                event['async_state_update'] == true ? '剧情完成，状态后台同步中…' : '生成完成';
          }
        });
        _scrollToBottom();
      }
      if (_legacyApi) {
        final story = done?['visible_story']?.toString() ?? _streamingText;
        if (mounted && story.isNotEmpty) {
          setState(() {
            _turns.add({
              'id': done?['turn_id'],
              'turn_number': done?['turn_number'] ?? _turns.length + 1,
              'user_input': opening ? '' : _formatInput(),
              'ai_response': story,
              'checker_result': done?['checker_result']
            });
            _streamingText = '';
          });
        }
        await _loadLegacy();
        if (mounted && done == null) {
          setState(() {
            _status = story.isEmpty
                ? '生成连接提前结束，请重试。'
                : '连接提前结束，已重新同步服务器存档；请检查本回内容是否完整。';
          });
        }
      } else {
        await _load();
        if (mounted) setState(() => _streamingText = '');
      }
    } catch (error) {
      final message = apiErrorMessage(error);
      if (_legacyApi) await _loadLegacy();
      if (mounted) setState(() => _status = message);
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  String _formatInput() {
    final values = <String>[];
    if (_action.text.trim().isNotEmpty) values.add('行动：${_action.text.trim()}');
    if (_dialogue.text.trim().isNotEmpty) {
      values.add('台词：${_dialogue.text.trim()}');
    }
    return values.join('\n');
  }

  Future<void> _regenerate(Map<String, dynamic> turn) async {
    final id = turn['id'];
    if (id == null) return;
    await _runStream(widget.api.postNdjson('/turns/$id/regenerate/stream', null,
        query: {'game_id': widget.gameId, 'turn_number': turn['turn_number']},
        headers: {'X-Request-ID': const Uuid().v4()}));
  }

  Future<void> _branch(Map<String, dynamic> turn) async {
    final id = turn['id'];
    if (id == null) return;
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
                title: const Text('从这里重新分支'),
                content: Text('第 ${turn['turn_number']} 轮及之后的剧情将删除，原输入会放回编辑框。'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(c, false),
                      child: const Text('取消')),
                  FilledButton(
                      onPressed: () => Navigator.pop(c, true),
                      child: const Text('继续'))
                ]));
    if (ok != true) return;
    try {
      await widget.api.deleteJson('/turns/$id/from-here', query: {
        'game_id': widget.gameId,
        'turn_number': turn['turn_number']
      });
      _action.text = turn['user_input']?.toString() ?? '';
      _dialogue.clear();
      await _load();
    } catch (e) {
      _snack(e);
    }
  }

  void _charactersSheet() {
    showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (c) => DraggableScrollableSheet(
            expand: false,
            initialChildSize: .65,
            builder: (_, controller) => ListView.builder(
                controller: controller,
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 24),
                itemCount: _characters.length,
                itemBuilder: (_, i) {
                  final item = _characters[i];
                  final avatar =
                      widget.api.mediaUrl(item['avatar_url']?.toString() ?? '');
                  return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                          leading: CharacterAvatar(
                            character: item,
                            avatarUrl: avatar,
                            size: 44,
                            showAutoBadge: true,
                          ),
                          title: Text(item['name']?.toString() ?? '未命名'),
                          subtitle: Text(
                              '${item['mood'] ?? '心情未设置'} · ${item['current_location'] ?? '位置未设置'}\n关系 ${item['relationship_score'] ?? 0} / 好感 ${item['affection_score'] ?? 0} / 信任 ${item['trust_score'] ?? 0}'),
                          isThreeLine: true));
                })));
  }

  void _snack(Object e) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 220), curve: Curves.easeOut);
      }
    });
  }

  @override
  void dispose() {
    _action.dispose();
    _dialogue.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          toolbarHeight: 64,
          titleSpacing: 4,
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_title, maxLines: 1, overflow: TextOverflow.ellipsis),
              Text(
                '互动剧情',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      fontWeight: FontWeight.w500,
                    ),
              ),
            ],
          ),
          actions: [
            IconButton(
              onPressed: _charactersSheet,
              tooltip: '角色状态',
              icon: const Icon(Icons.group_outlined),
            ),
            IconButton(
              onPressed: _load,
              tooltip: '刷新剧情',
              icon: const Icon(Icons.refresh_rounded),
            ),
            const SizedBox(width: 4),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  if (_game.isNotEmpty) _contextStrip(),
                  Expanded(child: _storyList()),
                  if (_status.isNotEmpty) _statusPill(),
                  _composer(),
                ],
              ),
      );

  Widget _contextStrip() {
    final currentState = _game['current_state']?.toString().trim() ?? '';
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom:
              BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 9),
        child: Row(
          children: [
            _metaChip(Icons.public_outlined,
                _world['name'] ?? _game['world_type'] ?? '未设置世界'),
            const SizedBox(width: 8),
            _metaChip(Icons.local_offer_outlined, _game['genre'] ?? '未设置题材'),
            const SizedBox(width: 8),
            _metaChip(
              Icons.bolt_outlined,
              currentState.isEmpty ? '进行中' : currentState,
              maxWidth: 210,
            ),
          ],
        ),
      ),
    );
  }

  Widget _metaChip(IconData icon, Object value, {double maxWidth = 150}) {
    final colors = Theme.of(context).colorScheme;
    return Tooltip(
      message: value.toString(),
      child: Container(
        constraints: BoxConstraints(maxWidth: maxWidth),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: colors.surfaceContainerLow,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 15, color: colors.primary),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                value.toString(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _storyList() {
    if (_turns.isEmpty && _streamingText.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.auto_stories_outlined,
                  size: 42,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
              ),
              const SizedBox(height: 20),
              Text('故事尚未开始', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                '让 AI 根据世界、角色和模板写下第一幕。',
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
              const SizedBox(height: 22),
              FilledButton.icon(
                onPressed: _generating ? null : _opening,
                icon: const Icon(Icons.auto_awesome),
                label: const Text('生成开场'),
              ),
            ],
          ),
        ),
      );
    }
    return ListView.builder(
      controller: _scroll,
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      itemCount:
          _turns.length + (_streamingText.isEmpty ? 0 : 1) + (_hasMore ? 1 : 0),
      itemBuilder: (_, rawIndex) {
        if (_hasMore && rawIndex == 0) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Center(
              child: OutlinedButton.icon(
                onPressed: _loadOlder,
                icon: const Icon(Icons.history, size: 18),
                label: const Text('加载更早剧情'),
              ),
            ),
          );
        }
        final index = rawIndex - (_hasMore ? 1 : 0);
        if (index == _turns.length) {
          return _storyTurn({'ai_response': _streamingText}, streaming: true);
        }
        return _storyTurn(_turns[index]);
      },
    );
  }

  Widget _statusPill() {
    final colors = Theme.of(context).colorScheme;
    final isError = _status.contains('失败') || _status.contains('错误');
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: isError ? colors.errorContainer : colors.secondaryContainer,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_generating)
              const Padding(
                padding: EdgeInsets.only(right: 8),
                child: SizedBox.square(
                  dimension: 13,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: Icon(
                    isError ? Icons.error_outline : Icons.check_circle_outline,
                    size: 16),
              ),
            Flexible(
              child: Text(
                _status,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _composer() {
    final colors = Theme.of(context).colorScheme;
    return SafeArea(
      top: false,
      child: Material(
        color: Colors.white,
        elevation: 10,
        shadowColor: Colors.black.withValues(alpha: .08),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Text('你的回合',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          )),
                  const Spacer(),
                  Text(
                    _autoComplete ? '智能补全已开' : '只按输入推进',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: colors.onSurfaceVariant,
                        ),
                  ),
                  const SizedBox(width: 4),
                  InkWell(
                    borderRadius: BorderRadius.circular(99),
                    onTap: () => setState(() => _autoComplete = !_autoComplete),
                    child: Padding(
                      padding: const EdgeInsets.all(6),
                      child: Icon(
                        _autoComplete
                            ? Icons.auto_fix_high
                            : Icons.auto_fix_off,
                        size: 20,
                        color: _autoComplete
                            ? colors.primary
                            : colors.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: SegmentedButton<String>(
                  style: const ButtonStyle(
                    visualDensity: VisualDensity.compact,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  showSelectedIcon: false,
                  segments: const [
                    ButtonSegment(value: 'instant', label: Text('极速')),
                    ButtonSegment(value: 'fast', label: Text('快速')),
                    ButtonSegment(value: 'full', label: Text('精细')),
                  ],
                  selected: {_mode},
                  onSelectionChanged: _generating
                      ? null
                      : (value) => setState(() => _mode = value.first),
                ),
              ),
              const SizedBox(height: 9),
              TextField(
                controller: _action,
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.newline,
                decoration: const InputDecoration(
                  hintText: '描述行动、背景，或希望剧情怎样回应…',
                  prefixIcon: Icon(Icons.directions_walk_outlined),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: _dialogue,
                      minLines: 1,
                      maxLines: 3,
                      textInputAction: TextInputAction.newline,
                      decoration: const InputDecoration(
                        hintText: '主角想说的话（可留空）',
                        prefixIcon: Icon(Icons.format_quote_rounded),
                      ),
                    ),
                  ),
                  const SizedBox(width: 9),
                  SizedBox.square(
                    dimension: 52,
                    child: IconButton.filled(
                      onPressed: _generating ? null : _submit,
                      tooltip: '发送这一回合',
                      icon: _generating
                          ? const SizedBox.square(
                              dimension: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.arrow_upward_rounded),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _storyTurn(Map<String, dynamic> turn, {bool streaming = false}) {
    final story = turn['ai_response']?.toString() ??
        turn['visible_story']?.toString() ??
        '';
    final input = turn['user_input']?.toString() ?? '';
    final segments = parseStory(story);
    final colors = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Divider(color: colors.outlineVariant)),
              const SizedBox(width: 10),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: colors.surfaceContainer,
                  borderRadius: BorderRadius.circular(99),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (streaming) ...[
                      const SizedBox.square(
                        dimension: 11,
                        child: CircularProgressIndicator(strokeWidth: 1.8),
                      ),
                      const SizedBox(width: 6),
                    ],
                    Text(
                      streaming
                          ? 'AI 正在续写'
                          : '第 ${turn['turn_number'] ?? turn['id'] ?? '-'} 回',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: colors.onSurfaceVariant,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ],
                ),
              ),
              if (!streaming && turn['id'] != null)
                PopupMenuButton<String>(
                  tooltip: '回合操作',
                  icon: const Icon(Icons.more_horiz, size: 20),
                  onSelected: (value) {
                    if (value == 'regenerate') _regenerate(turn);
                    if (value == 'branch') _branch(turn);
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(
                      value: 'regenerate',
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.refresh_rounded),
                        title: Text('重新生成这一回'),
                      ),
                    ),
                    PopupMenuItem(
                      value: 'branch',
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.call_split_rounded),
                        title: Text('从这里重新分支'),
                      ),
                    ),
                  ],
                )
              else
                const SizedBox(width: 10),
              Expanded(child: Divider(color: colors.outlineVariant)),
            ],
          ),
          if (input.trim().isNotEmpty) ...[
            const SizedBox(height: 13),
            _playerIntent(input),
          ],
          const SizedBox(height: 14),
          if (segments.isEmpty)
            _narrationBlock(story.isEmpty && streaming ? '正在构思下一段剧情…' : story)
          else
            ...segments.map(_storySegment),
        ],
      ),
    );
  }

  Widget _storySegment(StorySegment segment) => switch (segment.type) {
        StorySegmentType.dialogue => _dialogueBubble(segment),
        StorySegmentType.thought => _thoughtBlock(segment.text),
        StorySegmentType.narration => _narrationBlock(segment.text),
      };

  Widget _narrationBlock(String text) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(17),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 3,
            height: 24,
            decoration: BoxDecoration(
              color: colors.primary.withValues(alpha: .65),
              borderRadius: BorderRadius.circular(99),
            ),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: SelectableText(
              text,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    height: 1.65,
                    color: colors.onSurface,
                  ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _thoughtBlock(String text) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(18, 0, 18, 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      decoration: BoxDecoration(
        color: colors.tertiaryContainer.withValues(alpha: .42),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.psychology_alt_outlined,
              size: 19, color: colors.onTertiaryContainer),
          const SizedBox(width: 9),
          Expanded(
            child: SelectableText(
              text,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    height: 1.55,
                    fontStyle: FontStyle.italic,
                    color: colors.onTertiaryContainer,
                  ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _dialogueBubble(StorySegment segment) {
    final character = _characterFor(segment.speaker);
    final isPlayer = _isProtagonist(character, segment.speaker);
    final colors = Theme.of(context).colorScheme;
    final bubbleColor = isPlayer
        ? colors.primaryContainer
        : _speakerColor(segment.speaker).withValues(alpha: .55);
    final foreground = isPlayer ? colors.onPrimaryContainer : colors.onSurface;
    final avatar = _speakerAvatar(segment.speaker, character);
    final content = Flexible(
      child: Column(
        crossAxisAlignment:
            isPlayer ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Text(
              isPlayer ? '${segment.speaker} · 主角' : segment.speaker,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: colors.onSurfaceVariant,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          const SizedBox(height: 4),
          Container(
            constraints: const BoxConstraints(maxWidth: 560),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
            decoration: BoxDecoration(
              color: bubbleColor,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(18),
                topRight: const Radius.circular(18),
                bottomLeft: Radius.circular(isPlayer ? 18 : 5),
                bottomRight: Radius.circular(isPlayer ? 5 : 18),
              ),
            ),
            child: SelectableText(
              segment.text,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    height: 1.5,
                    color: foreground,
                  ),
            ),
          ),
        ],
      ),
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 11),
      child: Row(
        mainAxisAlignment:
            isPlayer ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: isPlayer
            ? [content, const SizedBox(width: 9), avatar]
            : [avatar, const SizedBox(width: 9), content],
      ),
    );
  }

  Widget _playerIntent(String rawInput) {
    final values = _inputParts(rawInput);
    final colors = Theme.of(context).colorScheme;
    final summary = [
      if (values.action.isNotEmpty) values.action,
      if (values.dialogue.isNotEmpty) '“${values.dialogue}”',
    ].join('  ·  ');
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 580),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
        decoration: BoxDecoration(
          color: colors.secondaryContainer.withValues(alpha: .7),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(16),
            bottomRight: Radius.circular(5),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.person_outline,
                size: 18, color: colors.onSecondaryContainer),
            const SizedBox(width: 7),
            Flexible(
              child: Text(
                summary.isEmpty ? rawInput.trim() : summary,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      height: 1.45,
                      color: colors.onSecondaryContainer,
                    ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  ({String action, String dialogue}) _inputParts(String input) {
    var action = '';
    var dialogue = '';
    for (final rawLine in input.split('\n')) {
      final line = rawLine.trim();
      if (line.startsWith('行动/背景/希望响应：') || line.startsWith('行动：')) {
        final value = line.split('：').skip(1).join('：').trim();
        if (!value.startsWith('<留空')) action = value;
      } else if (line.startsWith('主角台词：') || line.startsWith('台词：')) {
        final value = line.split('：').skip(1).join('：').trim();
        if (!value.startsWith('<留空')) dialogue = value;
      }
    }
    if (action.isEmpty && dialogue.isEmpty && !input.contains('【玩家回合输入】')) {
      action = input.trim();
    }
    return (action: action, dialogue: dialogue);
  }

  Map<String, dynamic>? _characterFor(String speaker) {
    final normalized = speaker.replaceAll(RegExp(r'\s+'), '');
    for (final character in _characters) {
      final name = character['name']?.toString().replaceAll(RegExp(r'\s+'), '');
      if (name == normalized) return character;
    }
    return null;
  }

  bool _isProtagonist(Map<String, dynamic>? character, String speaker) {
    final role = character?['role_type']?.toString().toLowerCase() ?? '';
    if (role == 'protagonist' || role == 'player' || role == '主角') return true;
    return speaker == '你' || speaker == '我';
  }

  Widget _speakerAvatar(String speaker, Map<String, dynamic>? character) {
    final avatarUrl =
        widget.api.mediaUrl(character?['avatar_url']?.toString() ?? '');
    return CharacterAvatar(
      character: character ?? <String, dynamic>{'name': speaker},
      avatarUrl: avatarUrl,
      size: 34,
    );
  }

  Color _speakerColor(String speaker) {
    final colors = Theme.of(context).colorScheme;
    final palette = [
      colors.secondaryContainer,
      colors.tertiaryContainer,
      colors.primaryContainer,
      const Color(0xFFFFE3D2),
      const Color(0xFFDDF1E5),
    ];
    final seed = speaker.codeUnits.fold<int>(0, (sum, value) => sum + value);
    return palette[seed % palette.length];
  }
}
