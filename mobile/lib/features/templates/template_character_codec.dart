import 'dart:convert';

class TemplateCharacterDecodeResult {
  const TemplateCharacterDecodeResult({
    required this.characters,
    this.hasError = false,
  });

  final List<Map<String, dynamic>> characters;
  final bool hasError;
}

/// Keeps the backend's historical template formats behind a structured UI.
class TemplateCharacterCodec {
  const TemplateCharacterCodec._();

  static const Map<String, dynamic> _baseDefaults = {
    'name': '重要角色',
    'role_type': 'npc',
    'avatar_url': '',
    'gender': '',
    'age': '',
    'race_or_identity': '',
    'appearance': '',
    'personality': '',
    'speech_style': '',
    'abilities': '',
    'current_location': '',
    'status': 'normal',
    'mood': '平静',
    'relationship_to_player': '待定',
    'relationship_score': 0,
    'affection_score': 0,
    'trust_score': 0,
    'tension_score': 0,
    'current_goal': '',
    'hidden_goal': '',
    'memory_summary': '故事刚开始，角色还没有长期记忆。',
    'agent_enabled': true,
    'extra_attrs': '{}',
  };

  static Map<String, dynamic> blank(String roleType) {
    final protagonist = roleType == 'protagonist';
    return {
      ..._baseDefaults,
      'name': protagonist ? '主角' : '重要角色',
      'role_type': protagonist ? 'protagonist' : 'npc',
      'relationship_to_player': protagonist ? '自己' : '待定',
      'agent_enabled': !protagonist,
    };
  }

  static TemplateCharacterDecodeResult decode(dynamic source) {
    if (source == null || (source is String && source.trim().isEmpty)) {
      return const TemplateCharacterDecodeResult(characters: []);
    }

    dynamic parsed = source;
    if (source is String) {
      try {
        parsed = jsonDecode(source);
      } catch (_) {
        return const TemplateCharacterDecodeResult(
          characters: [],
          hasError: true,
        );
      }
    }

    final extracted = <Map<String, dynamic>>[];
    var hasError = false;

    void appendItems(dynamic value, {String fallbackRole = 'npc'}) {
      final items = value is List ? value : [value];
      for (final item in items) {
        if (item is Map) {
          extracted.add(_normalize(
            Map<String, dynamic>.from(item),
            fallbackRole: fallbackRole,
          ));
        } else if (item != null) {
          hasError = true;
        }
      }
    }

    if (parsed is List) {
      appendItems(parsed);
    } else if (parsed is Map) {
      final data = Map<String, dynamic>.from(parsed);
      final direct = data['characters'] ??
          data['starter_characters'] ??
          data['默认角色'] ??
          data['开场角色'];
      if (direct is List) {
        appendItems(direct);
      } else {
        final protagonist = data['protagonist'] ?? data['主角'];
        final npcs =
            data['npcs'] ?? data['NPC'] ?? data['重要NPC'] ?? data['重要 NPC'];
        if (protagonist != null) {
          appendItems(protagonist, fallbackRole: 'protagonist');
        }
        if (npcs != null) appendItems(npcs);
        if (protagonist == null && npcs == null && data.isNotEmpty) {
          hasError = true;
        }
      }
    } else {
      hasError = true;
    }

    return TemplateCharacterDecodeResult(
      characters: extracted,
      hasError: hasError,
    );
  }

  static String encode(Iterable<Map<String, dynamic>> characters) {
    final normalized = characters.map((item) {
      final clean = <String, dynamic>{};
      for (final entry in item.entries) {
        if (!entry.key.startsWith('__')) clean[entry.key] = entry.value;
      }
      return _normalize(clean);
    }).toList();
    return const JsonEncoder.withIndent('  ').convert({
      'characters': normalized,
    });
  }

  static Map<String, dynamic> _normalize(
    Map<String, dynamic> source, {
    String fallbackRole = 'npc',
  }) {
    final rawRole = source['role_type']?.toString();
    final role = rawRole == 'protagonist' || fallbackRole == 'protagonist'
        ? 'protagonist'
        : 'npc';
    final result = <String, dynamic>{
      ...blank(role),
      ...source,
      'role_type': role,
    };
    result['name'] = _text(result['name']).isEmpty
        ? (role == 'protagonist' ? '主角' : '重要角色')
        : _text(result['name']);
    for (final key in const [
      'relationship_score',
      'affection_score',
      'trust_score',
      'tension_score',
    ]) {
      result[key] = _integer(result[key]);
    }
    result['agent_enabled'] = _boolean(
      result['agent_enabled'],
      fallback: role != 'protagonist',
    );
    if (result['extra_attrs'] is Map || result['extra_attrs'] is List) {
      result['extra_attrs'] = jsonEncode(result['extra_attrs']);
    } else {
      result['extra_attrs'] = _text(result['extra_attrs'], fallback: '{}');
    }
    return result;
  }

  static String _text(dynamic value, {String fallback = ''}) {
    if (value == null) return fallback;
    return value.toString();
  }

  static int _integer(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static bool _boolean(dynamic value, {required bool fallback}) {
    if (value is bool) return value;
    if (value is num) return value != 0;
    final text = value?.toString().trim().toLowerCase();
    if (const {'true', '1', 'yes', 'on'}.contains(text)) return true;
    if (const {'false', '0', 'no', 'off'}.contains(text)) return false;
    return fallback;
  }
}
