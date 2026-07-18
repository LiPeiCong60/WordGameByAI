import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/core/network/api_client.dart';
import 'package:word_game_by_ai/core/network/token_store.dart';
import 'package:word_game_by_ai/features/management/game_agent_page.dart';

class _FakeApiClient extends ApiClient {
  _FakeApiClient() : super(TokenStore());

  Map<String, dynamic>? sentBody;
  bool applied = false;

  @override
  Future<List<dynamic>> getList(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    if (path == '/games/0/management/sessions') {
      return [
        {'id': 7, 'title': '滨海模板对话'},
      ];
    }
    if (path == '/management/sessions/7/messages') {
      return [
        {
          'proposal_id': 11,
          'user_request': '我想生成一个滨海小城的恋爱模板。',
          'agent_response': '我会结合你的想法继续完善。',
          'proposed_actions': const [],
          'status': 'draft',
          'requires_confirmation': false,
        },
      ];
    }
    return const [];
  }

  @override
  Future<Map<String, dynamic>> postJson(
    String path, [
    Map<String, dynamic>? body,
    Map<String, dynamic>? query,
  ]) async {
    if (path == '/management/sessions/7/chat') {
      sentBody = body;
      return {
        'reply': '已沿用上一轮要求，自动补全完整模板。',
        'proposal_id': 12,
        'requires_confirmation': true,
        'proposed_actions': [
          {
            'action': 'create_template',
            'fields': {
              'name': '滨海心事',
              'default_character_fields': {
                'characters': [
                  {'name': '林屿', 'role_type': 'protagonist'},
                  {'name': '夏栀', 'role_type': 'npc'},
                ],
              },
            },
          },
        ],
      };
    }
    if (path == '/management/proposals/12/apply') {
      applied = true;
      return {'ok': true, 'status': 'applied'};
    }
    return <String, dynamic>{};
  }
}

void main() {
  testWidgets('模板助手恢复历史、继承编辑上下文并展示可读方案', (tester) async {
    final api = _FakeApiClient();
    await tester.pumpWidget(
      MaterialApp(
        home: GameAgentPage(
          api: api,
          gameId: 0,
          templateContext: const {
            'current_template_id': 3,
            'name': '滨海旧模板',
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('我想生成一个滨海小城的恋爱模板。'), findsOneWidget);
    expect(find.text('我会结合你的想法继续完善。'), findsOneWidget);

    final input = find.byType(TextField).last;
    await tester.enterText(input, '你帮我自动生成吧');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(api.sentBody?['scope'], '模板');
    expect(api.sentBody?['message'], contains('current_template_id'));
    expect(api.sentBody?['message'], contains('你帮我自动生成吧'));
    expect(find.text('你帮我自动生成吧'), findsOneWidget);
    expect(find.text('已沿用上一轮要求，自动补全完整模板。'), findsOneWidget);
    expect(find.textContaining('创建模板「滨海心事」 · 2 位开局角色'), findsOneWidget);
    expect(find.textContaining('create_template'), findsNothing);

    await tester.tap(find.text('确认执行'));
    await tester.pumpAndSettle();
    expect(api.applied, isTrue);
    expect(find.textContaining('模板方案已创建或更新'), findsOneWidget);
  });
}
