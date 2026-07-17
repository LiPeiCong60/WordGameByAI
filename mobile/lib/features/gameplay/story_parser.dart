enum StorySegmentType { narration, thought, dialogue }

class StorySegment {
  const StorySegment({
    required this.type,
    required this.text,
    this.speaker = '',
  });

  final StorySegmentType type;
  final String text;
  final String speaker;

  @override
  bool operator ==(Object other) =>
      other is StorySegment &&
      other.type == type &&
      other.text == text &&
      other.speaker == speaker;

  @override
  int get hashCode => Object.hash(type, text, speaker);
}

final _speakerPattern = RegExp(r'([\u3400-\u9fffA-Za-z0-9_·・]{1,20})[：:]');
const _nonSpeakerLabels = {
  '世界',
  '题材',
  '状态',
  '当前时间',
  '当前位置',
  '当前状态',
  '行动',
  '台词',
  '主角台词',
  '玩家指令',
};

List<StorySegment> parseStory(String source) {
  final text = source.replaceAll('\r\n', '\n').replaceAll('\r', '\n').trim();
  if (text.isEmpty) return const [];

  final segments = <StorySegment>[];
  var index = 0;
  while (index < text.length) {
    while (index < text.length && _isWhitespace(text[index])) {
      index++;
    }
    if (index >= text.length) break;

    final opener = text[index];
    final closer = switch (opener) {
      '[' => ']',
      '【' => '】',
      '(' => ')',
      '（' => '）',
      _ => '',
    };
    if (closer.isNotEmpty) {
      final end = text.indexOf(closer, index + 1);
      final content =
          end < 0 ? text.substring(index + 1) : text.substring(index + 1, end);
      _add(
        segments,
        opener == '(' || opener == '（'
            ? StorySegmentType.thought
            : StorySegmentType.narration,
        content,
      );
      index = end < 0 ? text.length : end + 1;
      continue;
    }

    final nextBoundary = _nextBoundary(text, index);
    _parsePlainChunk(text.substring(index, nextBoundary), segments);
    index = nextBoundary;
  }
  return segments;
}

int _nextBoundary(String text, int start) {
  var result = text.length;
  for (final marker in const ['\n', '[', '【', '(', '（']) {
    final found = text.indexOf(marker, start + 1);
    if (found >= 0 && found < result) result = found;
  }
  return result;
}

void _parsePlainChunk(String chunk, List<StorySegment> output) {
  final value = chunk.trim();
  if (value.isEmpty) return;

  final markers = <RegExpMatch>[];
  for (final match in _speakerPattern.allMatches(value)) {
    final speaker = match.group(1) ?? '';
    if (_nonSpeakerLabels.contains(speaker)) continue;
    if (match.start == 0 || _isSpeakerBoundary(value[match.start - 1])) {
      markers.add(match);
    }
  }
  if (markers.isEmpty) {
    _add(output, StorySegmentType.narration, value);
    return;
  }

  final prefix = value.substring(0, markers.first.start).trim();
  if (prefix.isNotEmpty) {
    _add(output, StorySegmentType.narration, prefix);
  }
  for (var i = 0; i < markers.length; i++) {
    final marker = markers[i];
    final end = i + 1 < markers.length ? markers[i + 1].start : value.length;
    final dialogue = value.substring(marker.end, end).trim();
    if (dialogue.isNotEmpty) {
      _add(
        output,
        StorySegmentType.dialogue,
        dialogue,
        speaker: marker.group(1) ?? '',
      );
    }
  }
}

void _add(
  List<StorySegment> output,
  StorySegmentType type,
  String text, {
  String speaker = '',
}) {
  final cleaned = text.trim();
  if (cleaned.isEmpty) return;
  output.add(StorySegment(type: type, text: cleaned, speaker: speaker.trim()));
}

bool _isWhitespace(String value) => value.trim().isEmpty;

bool _isSpeakerBoundary(String value) =>
    value.trim().isEmpty || '。！？!?；;'.contains(value);
