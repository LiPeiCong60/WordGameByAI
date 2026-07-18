import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/features/templates/template_editor_page.dart';

void main() {
  testWidgets('结构化编辑器加载、编辑、新增和删除角色', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(MaterialApp(
      home: TemplateEditorPage(
        title: '编辑模板',
        isAdmin: false,
        initial: {
          'name': '滨海之恋',
          'genre': '都市恋爱',
          'default_character_fields': jsonEncode({
            'characters': [
              {
                'name': '程予安',
                'role_type': 'protagonist',
                'personality': '温和',
              },
              {
                'name': '许晚',
                'role_type': 'npc',
                'personality': '独立',
              },
            ],
          }),
        },
        onSave: (data) async => saved = data,
      ),
    ));

    expect(find.textContaining('JSON'), findsNothing);

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('template-character-0')),
      500,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('程予安'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('template-character-1')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('许晚'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('edit-character-0')),
      -400,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const ValueKey('edit-character-0')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('character-name')),
      '程予安·主角',
    );
    await tester.tap(find.byKey(const ValueKey('save-character')));
    await tester.pumpAndSettle();
    expect(find.text('程予安·主角'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('remove-character-1')),
      400,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const ValueKey('remove-character-1')));
    await tester.pump();
    expect(find.text('许晚'), findsNothing);

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('add-npc')),
      400,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const ValueKey('add-npc')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('character-name')),
      '沈潮',
    );
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('character-relationship_score')),
      400,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.enterText(
      find.byKey(const ValueKey('character-relationship_score')),
      '18',
    );
    await tester.tap(find.byKey(const ValueKey('save-character')));
    await tester.pumpAndSettle();
    expect(find.text('沈潮'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('save-template')));
    await tester.pumpAndSettle();

    expect(saved, isNotNull);
    expect(saved!['default_character_fields'], isA<String>());
    final payload = jsonDecode(saved!['default_character_fields'] as String)
        as Map<String, dynamic>;
    final characters = payload['characters'] as List;
    expect(characters, hasLength(2));
    expect(characters.first['name'], '程予安·主角');
    expect(characters.last['name'], '沈潮');
    expect(characters.last['role_type'], 'npc');
    expect(characters.last['relationship_score'], 18);
  });

  testWidgets('新增主角并序列化全部结构化字段', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(MaterialApp(
      home: TemplateEditorPage(
        title: '新增模板',
        isAdmin: true,
        initial: const {
          'name': '侦探之夜',
          'default_character_fields': '{"characters":[]}',
        },
        onSave: (data) async => saved = data,
      ),
    ));

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('add-protagonist')),
      500,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const ValueKey('add-protagonist')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('character-name')),
      '林澜',
    );
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('character-race_or_identity')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.enterText(
      find.byKey(const ValueKey('character-race_or_identity')),
      '私家侦探',
    );
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('character-hidden_goal')),
      500,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.enterText(
      find.byKey(const ValueKey('character-hidden_goal')),
      '查清旧案真相',
    );
    await tester.tap(find.byKey(const ValueKey('save-character')));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('template-is-public')),
      -500,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.byKey(const ValueKey('template-is-public')));
    await tester.tap(find.byKey(const ValueKey('save-template')));
    await tester.pumpAndSettle();

    final payload = jsonDecode(saved!['default_character_fields'] as String)
        as Map<String, dynamic>;
    final character = (payload['characters'] as List).single;
    expect(saved!['is_public'], isTrue);
    expect(character['role_type'], 'protagonist');
    expect(character['race_or_identity'], '私家侦探');
    expect(character['hidden_goal'], '查清旧案真相');
    expect(character['agent_enabled'], isFalse);
  });

  testWidgets('损坏的旧配置不会被静默覆盖', (tester) async {
    Map<String, dynamic>? saved;
    await tester.pumpWidget(MaterialApp(
      home: TemplateEditorPage(
        title: '编辑模板',
        isAdmin: false,
        initial: const {
          'name': '旧模板',
          'default_character_fields': '{broken',
        },
        onSave: (data) async => saved = data,
      ),
    ));

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('reset-character-config')),
      500,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.textContaining('无法识别'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('save-template')));
    await tester.pump();
    expect(saved, isNull);
    expect(find.byKey(const ValueKey('template-editor-error')), findsOneWidget);

    await tester.ensureVisible(
      find.byKey(const ValueKey('reset-character-config')),
    );
    await tester.tap(find.byKey(const ValueKey('reset-character-config')));
    await tester.pump();
    expect(find.text('主角'), findsWidgets);
    expect(find.text('重要角色'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('save-template')));
    await tester.pumpAndSettle();
    final payload = jsonDecode(saved!['default_character_fields'] as String)
        as Map<String, dynamic>;
    expect(payload['characters'], hasLength(2));
  });
}
