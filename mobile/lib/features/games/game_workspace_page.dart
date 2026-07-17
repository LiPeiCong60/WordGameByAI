import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../gameplay/gameplay_page.dart';
import '../management/characters_page.dart';
import '../management/game_agent_page.dart';
import '../management/game_settings_page.dart';
import '../management/lore_page.dart';
import '../management/worlds_page.dart';

class GameWorkspacePage extends StatefulWidget {
  const GameWorkspacePage({super.key, required this.api, required this.game});
  final ApiClient api;
  final Map<String, dynamic> game;

  @override
  State<GameWorkspacePage> createState() => _GameWorkspacePageState();
}

class _GameWorkspacePageState extends State<GameWorkspacePage> {
  int _index = 0;
  late Map<String, dynamic> _game = {...widget.game};

  void _updateGame(Map<String, dynamic> game) => setState(() => _game = game);

  @override
  Widget build(BuildContext context) {
    final gameId = _game['id'] as int;
    final pages = [
      GameplayPage(api: widget.api, gameId: gameId),
      GameSettingsPage(api: widget.api, game: _game, onUpdated: _updateGame),
      CharactersPage(api: widget.api, gameId: gameId),
      WorldsPage(api: widget.api, gameId: gameId),
      LorePage(api: widget.api, gameId: gameId),
      GameAgentPage(api: widget.api, gameId: gameId),
    ];
    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(
            top:
                BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
          ),
        ),
        child: NavigationBar(
          selectedIndex: _index,
          labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
          onDestinationSelected: (value) => setState(() => _index = value),
          destinations: const [
            NavigationDestination(
                icon: Icon(Icons.auto_stories_outlined),
                selectedIcon: Icon(Icons.auto_stories),
                label: '剧情'),
            NavigationDestination(
                icon: Icon(Icons.tune_outlined),
                selectedIcon: Icon(Icons.tune),
                label: '存档'),
            NavigationDestination(
                icon: Icon(Icons.groups_outlined),
                selectedIcon: Icon(Icons.groups),
                label: '角色'),
            NavigationDestination(
                icon: Icon(Icons.public_outlined),
                selectedIcon: Icon(Icons.public),
                label: '世界'),
            NavigationDestination(
                icon: Icon(Icons.menu_book_outlined),
                selectedIcon: Icon(Icons.menu_book),
                label: '设定'),
            NavigationDestination(
                icon: Icon(Icons.smart_toy_outlined),
                selectedIcon: Icon(Icons.smart_toy),
                label: '助手'),
          ],
        ),
      ),
    );
  }
}
