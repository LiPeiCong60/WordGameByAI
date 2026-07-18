import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/features/templates/template_character_codec.dart';

void main() {
  group('TemplateCharacterCodec', () {
    test('解析现代格式并规范化字段类型', () {
      final result = TemplateCharacterCodec.decode(jsonEncode({
        'characters': [
          {
            'name': '林澜',
            'role_type': 'protagonist',
            'relationship_score': '12',
            'agent_enabled': 'false',
            'future_field': '保留扩展',
          },
        ],
      }));

      expect(result.hasError, isFalse);
      expect(result.characters, hasLength(1));
      expect(result.characters.single['name'], '林澜');
      expect(result.characters.single['relationship_score'], 12);
      expect(result.characters.single['agent_enabled'], isFalse);
      expect(result.characters.single['future_field'], '保留扩展');
    });

    test('兼容根数组和旧版主角 NPC 格式', () {
      final rootList = TemplateCharacterCodec.decode('[{"name":"陆川"}]');
      final legacy = TemplateCharacterCodec.decode(jsonEncode({
        'protagonist': {'name': '程予安'},
        'npcs': [
          {'name': '许晚'},
        ],
      }));
      final starterCharacters = TemplateCharacterCodec.decode(jsonEncode({
        'starter_characters': [
          {'name': '周野', 'role_type': 'npc'},
        ],
      }));

      expect(rootList.characters.single['name'], '陆川');
      expect(legacy.characters, hasLength(2));
      expect(legacy.characters.first['role_type'], 'protagonist');
      expect(legacy.characters.last['role_type'], 'npc');
      expect(starterCharacters.characters.single['name'], '周野');
    });

    test('损坏或不受支持的格式返回可识别错误', () {
      final broken = TemplateCharacterCodec.decode('{broken');
      final scalar = TemplateCharacterCodec.decode('42');

      expect(broken.hasError, isTrue);
      expect(broken.characters, isEmpty);
      expect(scalar.hasError, isTrue);
    });

    test('序列化为后端兼容的字符串并保留扩展字段', () {
      final encoded = TemplateCharacterCodec.encode([
        {
          ...TemplateCharacterCodec.blank('npc'),
          'name': '许晚',
          'affection_score': '7',
          'agent_enabled': 1,
          'future_field': {'source': 'legacy'},
          '__local_id': 9,
        },
      ]);
      final payload = jsonDecode(encoded) as Map<String, dynamic>;
      final character =
          (payload['characters'] as List).single as Map<String, dynamic>;

      expect(encoded, isA<String>());
      expect(character['affection_score'], 7);
      expect(character['agent_enabled'], isTrue);
      expect(character['future_field'], {'source': 'legacy'});
      expect(character.containsKey('__local_id'), isFalse);
    });
  });
}
