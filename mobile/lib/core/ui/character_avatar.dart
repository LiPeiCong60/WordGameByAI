import 'dart:math' as math;

import 'package:flutter/material.dart';

enum AvatarGender { male, female }

enum AvatarAge { child, teen, young, middle, senior }

class DefaultAvatarProfile {
  const DefaultAvatarProfile({
    required this.id,
    required this.label,
    required this.assetPath,
    required this.gender,
    required this.age,
    this.keywords = const [],
  });

  final String id;
  final String label;
  final String assetPath;
  final AvatarGender gender;
  final AvatarAge age;
  final List<String> keywords;
}

class DefaultAvatarCatalog {
  const DefaultAvatarCatalog._();

  static const profiles = <DefaultAvatarProfile>[
    DefaultAvatarProfile(
      id: 'child_boy_cheerful',
      label: '活泼男孩',
      assetPath: 'assets/avatars/child_boy_cheerful.png',
      gender: AvatarGender.male,
      age: AvatarAge.child,
      keywords: ['活泼', '开朗', '阳光', '好动', '调皮', '天真', 'cheerful'],
    ),
    DefaultAvatarProfile(
      id: 'child_girl_curious',
      label: '好奇女孩',
      assetPath: 'assets/avatars/child_girl_curious.png',
      gender: AvatarGender.female,
      age: AvatarAge.child,
      keywords: ['好奇', '文静', '乖巧', '天真', '温柔', 'curious'],
    ),
    DefaultAvatarProfile(
      id: 'teen_boy_quiet',
      label: '沉静少年',
      assetPath: 'assets/avatars/teen_boy_quiet.png',
      gender: AvatarGender.male,
      age: AvatarAge.teen,
      keywords: ['安静', '沉默', '冷淡', '内向', '理性', '学生', 'quiet'],
    ),
    DefaultAvatarProfile(
      id: 'teen_girl_lively',
      label: '灵动少女',
      assetPath: 'assets/avatars/teen_girl_lively.png',
      gender: AvatarGender.female,
      age: AvatarAge.teen,
      keywords: ['活泼', '自信', '飒爽', '运动', '学生', '灵动', 'lively'],
    ),
    DefaultAvatarProfile(
      id: 'young_man_refined',
      label: '俊朗青年',
      assetPath: 'assets/avatars/young_man_refined.png',
      gender: AvatarGender.male,
      age: AvatarAge.young,
      keywords: ['俊', '帅', '英俊', '清秀', '儒雅', '精致', '优雅', '贵公子', 'handsome'],
    ),
    DefaultAvatarProfile(
      id: 'young_woman_elegant',
      label: '优雅青年',
      assetPath: 'assets/avatars/young_woman_elegant.png',
      gender: AvatarGender.female,
      age: AvatarAge.young,
      keywords: ['美', '漂亮', '优雅', '明艳', '精致', '妩媚', '绝色', 'elegant'],
    ),
    DefaultAvatarProfile(
      id: 'young_man_rugged',
      label: '硬朗青年',
      assetPath: 'assets/avatars/young_man_rugged.png',
      gender: AvatarGender.male,
      age: AvatarAge.young,
      keywords: ['粗犷', '沧桑', '强壮', '硬汉', '疤', '凶', '不修边幅', '丑', 'rugged'],
    ),
    DefaultAvatarProfile(
      id: 'young_woman_approachable',
      label: '亲和青年',
      assetPath: 'assets/avatars/young_woman_approachable.png',
      gender: AvatarGender.female,
      age: AvatarAge.young,
      keywords: ['普通', '朴素', '平凡', '雀斑', '亲和', '温柔', '短发', '自然'],
    ),
    DefaultAvatarProfile(
      id: 'middle_man_stern',
      label: '沉稳中年',
      assetPath: 'assets/avatars/middle_man_stern.png',
      gender: AvatarGender.male,
      age: AvatarAge.middle,
      keywords: ['严肃', '威严', '沉稳', '成熟', '老板', '父亲', '干练', 'stern'],
    ),
    DefaultAvatarProfile(
      id: 'middle_woman_capable',
      label: '干练中年',
      assetPath: 'assets/avatars/middle_woman_capable.png',
      gender: AvatarGender.female,
      age: AvatarAge.middle,
      keywords: ['干练', '成熟', '母亲', '职业', '沉稳', '女强人', 'capable'],
    ),
    DefaultAvatarProfile(
      id: 'senior_man_wise',
      label: '睿智长者',
      assetPath: 'assets/avatars/senior_man_wise.png',
      gender: AvatarGender.male,
      age: AvatarAge.senior,
      keywords: ['睿智', '长者', '爷爷', '胡须', '慈祥', '博学', 'wise'],
    ),
    DefaultAvatarProfile(
      id: 'senior_woman_kind',
      label: '慈祥长者',
      assetPath: 'assets/avatars/senior_woman_kind.png',
      gender: AvatarGender.female,
      age: AvatarAge.senior,
      keywords: ['慈祥', '奶奶', '和蔼', '长者', '温暖', '坚韧', 'kind'],
    ),
  ];

  static DefaultAvatarProfile match(Map<String, dynamic> character) {
    final name = _value(character, 'name');
    final genderText = '${_value(character, 'gender')} '
            '${_value(character, 'race_or_identity')}'
        .toLowerCase();
    final allText = [
      name,
      genderText,
      _value(character, 'age'),
      _value(character, 'race_or_identity'),
      _value(character, 'appearance'),
      _value(character, 'personality'),
      _value(character, 'role_type'),
    ].join(' ').toLowerCase();
    final gender = _inferGender(genderText);
    final age = _inferAge(_value(character, 'age'), allText);

    DefaultAvatarProfile? winner;
    var bestScore = -1 << 30;
    for (final profile in profiles) {
      var score = 0;
      if (gender != null) {
        score += profile.gender == gender ? 1000 : -1000;
      }
      if (age != null) {
        final distance = (profile.age.index - age.index).abs();
        score += 700 - distance * 420;
      }
      for (final keyword in profile.keywords) {
        if (allText.contains(keyword)) score += 90;
      }
      score += _stableHash('$name:${profile.id}') % 31;
      if (score > bestScore) {
        bestScore = score;
        winner = profile;
      }
    }
    return winner!;
  }

  static String _value(Map<String, dynamic> character, String key) =>
      character[key]?.toString().trim() ?? '';

  static AvatarGender? _inferGender(String text) {
    final normalized = text.toLowerCase();
    if (_containsAny(normalized,
        ['女性', '女生', '女孩', '女子', '女人', 'female', 'woman', 'girl'])) {
      return AvatarGender.female;
    }
    if (_containsAny(
        normalized, ['男性', '男生', '男孩', '男子', '男人', 'male', 'man', 'boy'])) {
      return AvatarGender.male;
    }
    if (RegExp(r'(^|[^女])男($|[^女])').hasMatch(normalized)) {
      return AvatarGender.male;
    }
    if (normalized.contains('女')) return AvatarGender.female;
    return null;
  }

  static AvatarAge? _inferAge(String ageText, String allText) {
    final cohort = RegExp(r'(?:(19|20))?(\d{2})后').firstMatch(ageText);
    if (cohort != null) {
      final decade = int.tryParse(cohort.group(2)!);
      if (decade != null) {
        if (decade <= 10) return AvatarAge.teen;
        if (decade <= 30) return AvatarAge.young;
        if (decade >= 90) return AvatarAge.young;
        if (decade >= 80) return AvatarAge.middle;
        return AvatarAge.senior;
      }
    }
    final number = RegExp(r'(?<!\d)(\d{1,3})(?!\d)').firstMatch(ageText);
    final years = number == null ? null : int.tryParse(number.group(1)!);
    if (years != null) {
      if (years <= 12) return AvatarAge.child;
      if (years <= 18) return AvatarAge.teen;
      if (years <= 39) return AvatarAge.young;
      if (years <= 59) return AvatarAge.middle;
      return AvatarAge.senior;
    }
    final normalized = '$ageText $allText'.toLowerCase();
    if (_containsAny(normalized,
        ['老年', '老人', '老者', '长者', '爷爷', '奶奶', '祖父', '祖母', 'elder', 'senior'])) {
      return AvatarAge.senior;
    }
    if (_containsAny(
        normalized, ['中年', '大叔', '叔叔', '阿姨', '壮年', 'middle-aged'])) {
      return AvatarAge.middle;
    }
    if (_containsAny(normalized, ['少年', '少女', '青少年', '中学生', '高中生', 'teen'])) {
      return AvatarAge.teen;
    }
    if (_containsAny(
        normalized, ['儿童', '孩子', '孩童', '小孩', '幼年', '幼童', 'child', 'kid'])) {
      return AvatarAge.child;
    }
    if (_containsAny(normalized, ['青年', '年轻', '大学生', 'young'])) {
      return AvatarAge.young;
    }
    return null;
  }

  static bool _containsAny(String text, List<String> values) =>
      values.any(text.contains);

  static int _stableHash(String value) {
    var hash = 0x811c9dc5;
    for (final unit in value.codeUnits) {
      hash ^= unit;
      hash = (hash * 0x01000193) & 0x7fffffff;
    }
    return hash;
  }
}

class CharacterAvatar extends StatelessWidget {
  const CharacterAvatar({
    super.key,
    required this.character,
    this.avatarUrl = '',
    this.size = 44,
    this.showAutoBadge = false,
  });

  final Map<String, dynamic> character;
  final String avatarUrl;
  final double size;
  final bool showAutoBadge;

  @override
  Widget build(BuildContext context) {
    final profile = DefaultAvatarCatalog.match(character);
    final pixelSize = math.max(
      64,
      (size * MediaQuery.devicePixelRatioOf(context)).round(),
    );
    final fallback = Image.asset(
      profile.assetPath,
      width: size,
      height: size,
      fit: BoxFit.cover,
      cacheWidth: pixelSize,
      cacheHeight: pixelSize,
    );
    final image = avatarUrl.trim().isEmpty
        ? fallback
        : Image.network(
            avatarUrl,
            width: size,
            height: size,
            fit: BoxFit.cover,
            cacheWidth: pixelSize,
            cacheHeight: pixelSize,
            errorBuilder: (_, __, ___) => fallback,
          );
    final name = character['name']?.toString().trim();
    return Semantics(
      image: true,
      label: '${name?.isNotEmpty == true ? name : '角色'}的头像'
          '${avatarUrl.trim().isEmpty ? '，智能匹配为${profile.label}' : ''}',
      child: SizedBox.square(
        dimension: size,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                    width: 1.5,
                  ),
                ),
                child: ClipOval(child: image),
              ),
            ),
            if (showAutoBadge && avatarUrl.trim().isEmpty)
              Positioned(
                right: -2,
                bottom: -2,
                child: Container(
                  width: math.max(16, size * .34),
                  height: math.max(16, size * .34),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primary,
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 1.5),
                  ),
                  child: const Icon(Icons.auto_awesome,
                      color: Colors.white, size: 10),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class DefaultAvatarPreview extends StatelessWidget {
  const DefaultAvatarPreview({
    super.key,
    required this.character,
    this.avatarUrl = '',
  });

  final Map<String, dynamic> character;
  final String avatarUrl;

  @override
  Widget build(BuildContext context) {
    final profile = DefaultAvatarCatalog.match(character);
    final uploaded = avatarUrl.trim().isNotEmpty;
    final colors = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.primaryContainer.withValues(alpha: .45),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colors.primary.withValues(alpha: .18)),
      ),
      child: Row(
        children: [
          CharacterAvatar(
            character: character,
            avatarUrl: avatarUrl,
            size: 72,
            showAutoBadge: true,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  uploaded ? '已使用上传头像' : '智能头像 · ${profile.label}',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  uploaded
                      ? '上传图片优先显示，可在角色菜单中恢复智能匹配。'
                      : '根据年龄、性别、身份、外貌和性格实时匹配。',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: colors.onSurfaceVariant, height: 1.35),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
