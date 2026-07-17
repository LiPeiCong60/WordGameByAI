import 'package:flutter_test/flutter_test.dart';
import 'package:word_game_by_ai/core/ui/character_avatar.dart';

void main() {
  group('DefaultAvatarCatalog', () {
    test('按明确年龄和性别匹配儿童头像', () {
      final profile = DefaultAvatarCatalog.match({
        'name': '小雨',
        'gender': '女',
        'age': '8岁',
        'personality': '文静、好奇',
      });

      expect(profile.id, 'child_girl_curious');
    });

    test('数值年龄能区分少年和中年', () {
      final teen = DefaultAvatarCatalog.match({
        'name': '陈默',
        'gender': '男',
        'age': '16',
        'personality': '安静内向',
      });
      final middle = DefaultAvatarCatalog.match({
        'name': '林岚',
        'gender': '女性',
        'age': '48岁',
        'appearance': '干练成熟',
      });

      expect(teen.id, 'teen_boy_quiet');
      expect(middle.id, 'middle_woman_capable');
    });

    test('同年龄性别下继续按外貌气质匹配', () {
      final refined = DefaultAvatarCatalog.match({
        'name': '顾川',
        'gender': '男',
        'age': '青年',
        'appearance': '清秀俊朗，气质儒雅',
      });
      final rugged = DefaultAvatarCatalog.match({
        'name': '周野',
        'gender': '男',
        'age': '29',
        'appearance': '粗犷沧桑，眉角有疤',
      });

      expect(refined.id, 'young_man_refined');
      expect(rugged.id, 'young_man_rugged');
    });

    test('老年标签不会错误匹配年轻头像', () {
      final profile = DefaultAvatarCatalog.match({
        'name': '沈伯',
        'gender': '男',
        'age': '老年长者',
        'personality': '睿智博学',
      });

      expect(profile.id, 'senior_man_wise');
    });

    test('90后按代际匹配青年而不是九十岁老人', () {
      final profile = DefaultAvatarCatalog.match({
        'name': '陆川',
        'gender': '男',
        'age': '90后',
        'appearance': '俊朗清秀',
      });

      expect(profile.id, 'young_man_refined');
    });

    test('完全没有标签时按姓名稳定匹配', () {
      final first = DefaultAvatarCatalog.match({'name': '无名旅人'});
      final second = DefaultAvatarCatalog.match({'name': '无名旅人'});

      expect(first.id, second.id);
      expect(DefaultAvatarCatalog.profiles, hasLength(12));
    });
  });
}
