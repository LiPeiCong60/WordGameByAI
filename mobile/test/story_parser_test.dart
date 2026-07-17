import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/features/gameplay/story_parser.dart';

void main() {
  test('提取相邻旁白、角色对白和心理活动', () {
    const source = '[七月的夜风从巷口灌进来。][手机屏幕亮起。]'
        '许晚：刚洗完澡。许晚：空调坏了。许晚：你呢，刚下班？'
        '[消息后面跟了一张照片。]'
        '（她的回复比平时更松散。）';

    expect(
      parseStory(source),
      const [
        StorySegment(type: StorySegmentType.narration, text: '七月的夜风从巷口灌进来。'),
        StorySegment(type: StorySegmentType.narration, text: '手机屏幕亮起。'),
        StorySegment(
            type: StorySegmentType.dialogue, speaker: '许晚', text: '刚洗完澡。'),
        StorySegment(
            type: StorySegmentType.dialogue, speaker: '许晚', text: '空调坏了。'),
        StorySegment(
            type: StorySegmentType.dialogue, speaker: '许晚', text: '你呢，刚下班？'),
        StorySegment(type: StorySegmentType.narration, text: '消息后面跟了一张照片。'),
        StorySegment(type: StorySegmentType.thought, text: '她的回复比平时更松散。'),
      ],
    );
  });

  test('同一行的多人对白仍能拆分', () {
    expect(
      parseStory('程予安：干嘛呢？许晚：刚洗完澡。'),
      const [
        StorySegment(
            type: StorySegmentType.dialogue, speaker: '程予安', text: '干嘛呢？'),
        StorySegment(
            type: StorySegmentType.dialogue, speaker: '许晚', text: '刚洗完澡。'),
      ],
    );
  });

  test('模型格式漂移时保留裸文本而不丢内容', () {
    expect(
      parseStory('夜色渐深，远处响起闷雷。'),
      const [
        StorySegment(type: StorySegmentType.narration, text: '夜色渐深，远处响起闷雷。'),
      ],
    );
  });
}
