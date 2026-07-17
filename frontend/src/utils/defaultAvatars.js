export const AVATAR_GENDERS = Object.freeze({
  male: 'male',
  female: 'female'
})

export const AVATAR_AGES = Object.freeze({
  child: 'child',
  teen: 'teen',
  young: 'young',
  middle: 'middle',
  senior: 'senior'
})

const AGE_ORDER = Object.freeze([
  AVATAR_AGES.child,
  AVATAR_AGES.teen,
  AVATAR_AGES.young,
  AVATAR_AGES.middle,
  AVATAR_AGES.senior
])

export const DEFAULT_AVATAR_PROFILES = Object.freeze([
  {
    id: 'child_boy_cheerful',
    label: '活泼男孩',
    assetPath: '/assets/avatars/child_boy_cheerful.webp',
    gender: AVATAR_GENDERS.male,
    age: AVATAR_AGES.child,
    keywords: ['活泼', '开朗', '阳光', '好动', '调皮', '天真', 'cheerful']
  },
  {
    id: 'child_girl_curious',
    label: '好奇女孩',
    assetPath: '/assets/avatars/child_girl_curious.webp',
    gender: AVATAR_GENDERS.female,
    age: AVATAR_AGES.child,
    keywords: ['好奇', '文静', '乖巧', '天真', '温柔', 'curious']
  },
  {
    id: 'teen_boy_quiet',
    label: '沉静少年',
    assetPath: '/assets/avatars/teen_boy_quiet.webp',
    gender: AVATAR_GENDERS.male,
    age: AVATAR_AGES.teen,
    keywords: ['安静', '沉默', '冷淡', '内向', '理性', '学生', 'quiet']
  },
  {
    id: 'teen_girl_lively',
    label: '灵动少女',
    assetPath: '/assets/avatars/teen_girl_lively.webp',
    gender: AVATAR_GENDERS.female,
    age: AVATAR_AGES.teen,
    keywords: ['活泼', '自信', '飒爽', '运动', '学生', '灵动', 'lively']
  },
  {
    id: 'young_man_refined',
    label: '俊朗青年',
    assetPath: '/assets/avatars/young_man_refined.webp',
    gender: AVATAR_GENDERS.male,
    age: AVATAR_AGES.young,
    keywords: ['俊', '帅', '英俊', '清秀', '儒雅', '精致', '优雅', '贵公子', 'handsome']
  },
  {
    id: 'young_woman_elegant',
    label: '优雅青年',
    assetPath: '/assets/avatars/young_woman_elegant.webp',
    gender: AVATAR_GENDERS.female,
    age: AVATAR_AGES.young,
    keywords: ['美', '漂亮', '优雅', '明艳', '精致', '妩媚', '绝色', 'elegant']
  },
  {
    id: 'young_man_rugged',
    label: '硬朗青年',
    assetPath: '/assets/avatars/young_man_rugged.webp',
    gender: AVATAR_GENDERS.male,
    age: AVATAR_AGES.young,
    keywords: ['粗犷', '沧桑', '强壮', '硬汉', '疤', '凶', '不修边幅', '丑', 'rugged']
  },
  {
    id: 'young_woman_approachable',
    label: '亲和青年',
    assetPath: '/assets/avatars/young_woman_approachable.webp',
    gender: AVATAR_GENDERS.female,
    age: AVATAR_AGES.young,
    keywords: ['普通', '朴素', '平凡', '雀斑', '亲和', '温柔', '短发', '自然']
  },
  {
    id: 'middle_man_stern',
    label: '沉稳中年',
    assetPath: '/assets/avatars/middle_man_stern.webp',
    gender: AVATAR_GENDERS.male,
    age: AVATAR_AGES.middle,
    keywords: ['严肃', '威严', '沉稳', '成熟', '老板', '父亲', '干练', 'stern']
  },
  {
    id: 'middle_woman_capable',
    label: '干练中年',
    assetPath: '/assets/avatars/middle_woman_capable.webp',
    gender: AVATAR_GENDERS.female,
    age: AVATAR_AGES.middle,
    keywords: ['干练', '成熟', '母亲', '职业', '沉稳', '女强人', 'capable']
  },
  {
    id: 'senior_man_wise',
    label: '睿智长者',
    assetPath: '/assets/avatars/senior_man_wise.webp',
    gender: AVATAR_GENDERS.male,
    age: AVATAR_AGES.senior,
    keywords: ['睿智', '长者', '爷爷', '胡须', '慈祥', '博学', 'wise']
  },
  {
    id: 'senior_woman_kind',
    label: '慈祥长者',
    assetPath: '/assets/avatars/senior_woman_kind.webp',
    gender: AVATAR_GENDERS.female,
    age: AVATAR_AGES.senior,
    keywords: ['慈祥', '奶奶', '和蔼', '长者', '温暖', '坚韧', 'kind']
  }
].map((profile) => Object.freeze({
  ...profile,
  keywords: Object.freeze(profile.keywords)
})))

function value(character, key) {
  const item = character?.[key]
  return item == null ? '' : String(item).trim()
}

function containsAny(text, values) {
  return values.some((item) => text.includes(item))
}

function inferGender(text) {
  const normalized = String(text || '').toLowerCase()
  if (containsAny(normalized, ['女性', '女生', '女孩', '女子', '女人', 'female', 'woman', 'girl'])) {
    return AVATAR_GENDERS.female
  }
  if (containsAny(normalized, ['男性', '男生', '男孩', '男子', '男人', 'male', 'man', 'boy'])) {
    return AVATAR_GENDERS.male
  }
  if (/(^|[^女])男($|[^女])/.test(normalized)) return AVATAR_GENDERS.male
  if (normalized.includes('女')) return AVATAR_GENDERS.female
  return null
}

function inferAge(ageText, allText) {
  const cohort = String(ageText || '').match(/(?:(19|20))?(\d{2})后/)
  if (cohort) {
    const decade = Number.parseInt(cohort[2], 10)
    if (Number.isFinite(decade)) {
      if (decade <= 10) return AVATAR_AGES.teen
      if (decade <= 30) return AVATAR_AGES.young
      if (decade >= 90) return AVATAR_AGES.young
      if (decade >= 80) return AVATAR_AGES.middle
      return AVATAR_AGES.senior
    }
  }

  const number = String(ageText || '').match(/(?:^|[^\d])(\d{1,3})(?!\d)/)
  const years = number ? Number.parseInt(number[1], 10) : null
  if (Number.isFinite(years)) {
    if (years <= 12) return AVATAR_AGES.child
    if (years <= 18) return AVATAR_AGES.teen
    if (years <= 39) return AVATAR_AGES.young
    if (years <= 59) return AVATAR_AGES.middle
    return AVATAR_AGES.senior
  }

  const normalized = `${ageText || ''} ${allText || ''}`.toLowerCase()
  if (containsAny(normalized, ['老年', '老人', '老者', '长者', '爷爷', '奶奶', '祖父', '祖母', 'elder', 'senior'])) {
    return AVATAR_AGES.senior
  }
  if (containsAny(normalized, ['中年', '大叔', '叔叔', '阿姨', '壮年', 'middle-aged'])) {
    return AVATAR_AGES.middle
  }
  if (containsAny(normalized, ['少年', '少女', '青少年', '中学生', '高中生', 'teen'])) {
    return AVATAR_AGES.teen
  }
  if (containsAny(normalized, ['儿童', '孩子', '孩童', '小孩', '幼年', '幼童', 'child', 'kid'])) {
    return AVATAR_AGES.child
  }
  if (containsAny(normalized, ['青年', '年轻', '大学生', 'young'])) {
    return AVATAR_AGES.young
  }
  return null
}

function stableHash(input) {
  let hash = 0x811c9dc5
  const text = String(input || '')
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193) & 0x7fffffff
  }
  return hash
}

/**
 * 根据角色标签稳定匹配默认头像。输入相同角色时，刷新页面也会得到同一头像。
 */
export function matchDefaultAvatar(character = {}) {
  const name = value(character, 'name')
  const genderText = `${value(character, 'gender')} ${value(character, 'race_or_identity')}`.toLowerCase()
  const allText = [
    name,
    genderText,
    value(character, 'age'),
    value(character, 'race_or_identity'),
    value(character, 'appearance'),
    value(character, 'personality'),
    value(character, 'role_type')
  ].join(' ').toLowerCase()
  const gender = inferGender(genderText)
  const age = inferAge(value(character, 'age'), allText)

  let winner = DEFAULT_AVATAR_PROFILES[0]
  let bestScore = Number.NEGATIVE_INFINITY
  for (const profile of DEFAULT_AVATAR_PROFILES) {
    let score = 0
    if (gender) score += profile.gender === gender ? 1000 : -1000
    if (age) {
      const distance = Math.abs(AGE_ORDER.indexOf(profile.age) - AGE_ORDER.indexOf(age))
      score += 700 - distance * 420
    }
    for (const keyword of profile.keywords) {
      if (allText.includes(keyword)) score += 90
    }
    score += stableHash(`${name}:${profile.id}`) % 31
    if (score > bestScore) {
      bestScore = score
      winner = profile
    }
  }
  return winner
}

export function defaultAvatarPath(character = {}) {
  return matchDefaultAvatar(character).assetPath
}
