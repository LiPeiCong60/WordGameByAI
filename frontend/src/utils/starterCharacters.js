import { createCharacter, listCharacters } from '../api/characters'

const genreStarters = {
  玄幻: [
    {
      name: '顾玄',
      role_type: 'protagonist',
      gender: '自定义',
      age: '18',
      race_or_identity: '初入修途的凡人弟子',
      personality: '沉稳、谨慎，对变强有强烈执念。',
      speech_style: '克制有礼，遇到危险时言简意赅。',
      abilities: '基础吐纳、剑术入门、灵气感知微弱。',
      mood: '警醒',
      current_goal: '通过入门试炼，确认自己的修行道路。',
      agent_enabled: false
    },
    {
      name: '洛凝霜',
      role_type: 'npc',
      gender: '女',
      age: '未知',
      race_or_identity: '宗门内门弟子',
      personality: '清冷、守规矩，但并非无情。',
      speech_style: '平静、简短，常以修行规矩提醒他人。',
      abilities: '御剑、寒属性灵力、宗门情报。',
      relationship_to_player: '考核引路人',
      relationship_score: 10
    }
  ],
  丧尸: [
    {
      name: '周临',
      role_type: 'protagonist',
      gender: '自定义',
      age: '26',
      race_or_identity: '普通幸存者',
      personality: '现实、谨慎，压力下仍会照顾同伴。',
      speech_style: '低声、直接，不浪费字句。',
      abilities: '基础急救、路线判断、临场应变。',
      mood: '紧绷',
      current_goal: '找到安全落脚点和可持续物资。',
      agent_enabled: false
    },
    {
      name: '林夏',
      role_type: 'npc',
      gender: '女',
      age: '24',
      race_or_identity: '幸存者同伴',
      personality: '冷静、警惕，对陌生人保持距离。',
      speech_style: '短句、低声，会快速指出风险。',
      abilities: '物资清点、基础射击、伤口处理。',
      relationship_to_player: '临时同伴',
      relationship_score: 25
    }
  ],
  快穿: [
    {
      name: '沈知微',
      role_type: 'protagonist',
      gender: '自定义',
      age: '未知',
      race_or_identity: '任务执行者',
      personality: '适应力强，习惯在陌生身份里快速找线索。',
      speech_style: '根据身份调整语气，内心分析清晰。',
      abilities: '身份伪装、剧情判断、任务拆解。',
      mood: '冷静',
      current_goal: '确认当前世界身份和任务目标。',
      agent_enabled: false
    },
    {
      name: '系统 07',
      role_type: 'npc',
      gender: '无',
      age: '未知',
      race_or_identity: '任务系统',
      personality: '理性、机械，但会在关键处给出提示。',
      speech_style: '简短、任务化，偶尔带冷幽默。',
      abilities: '任务播报、剧情偏移监测、基础信息检索。',
      relationship_to_player: '绑定系统',
      relationship_score: 50
    }
  ],
  科幻: [
    {
      name: '陆星野',
      role_type: 'protagonist',
      gender: '自定义',
      age: '29',
      race_or_identity: '远征队成员',
      personality: '理性、耐心，对未知保持敬畏。',
      speech_style: '冷静、准确，习惯确认数据再行动。',
      abilities: '外勤探索、设备维护、风险评估。',
      mood: '专注',
      current_goal: '完成当前星域的初步勘测。',
      agent_enabled: false
    },
    {
      name: '诺亚',
      role_type: 'npc',
      gender: '无',
      age: '未知',
      race_or_identity: '舰载 AI',
      personality: '精确、克制，对船员安全有优先级。',
      speech_style: '数据化、简洁，必要时给出风险等级。',
      abilities: '舰船监控、资料检索、环境分析。',
      relationship_to_player: '舰载协助系统',
      relationship_score: 40
    }
  ],
  都市: [
    {
      name: '程予安',
      role_type: 'protagonist',
      gender: '自定义',
      age: '22',
      race_or_identity: '都市青年 / 自定义身份',
      personality: '温和但有主见，习惯把情绪藏在玩笑后面。',
      speech_style: '自然、松弛，熟人面前会带一点调侃。',
      abilities: '观察细节、社交判断、基础生活能力。',
      mood: '略疲惫但期待变化',
      current_goal: '在日常生活里找到新的关系转机。',
      agent_enabled: false
    },
    {
      name: '许晚',
      role_type: 'npc',
      gender: '女',
      age: '22',
      race_or_identity: '重要关系角色',
      personality: '敏感、独立，表面冷静但很在意细节。',
      speech_style: '简洁直接，偶尔用轻描淡写掩饰关心。',
      abilities: '情绪观察、信息整理、城市生活经验。',
      relationship_to_player: '熟人',
      relationship_score: 35
    }
  ]
}

const defaultStarters = [
  {
    name: '主角',
    role_type: 'protagonist',
    gender: '自定义',
    age: '自定义',
    race_or_identity: '自定义身份',
    personality: '等待用户设定。',
    speech_style: '跟随用户设定。',
    abilities: '跟随用户设定。',
    mood: '平静',
    current_goal: '确认当前处境。',
    agent_enabled: false
  },
  {
    name: '重要角色',
    role_type: 'npc',
    gender: '自定义',
    age: '自定义',
    race_or_identity: '自定义身份',
    personality: '等待用户设定。',
    speech_style: '跟随用户设定。',
    abilities: '跟随用户设定。',
    relationship_to_player: '待定',
    relationship_score: 0
  }
]

function openingLocation(game) {
  return game?.current_state || game?.world_type || '开场地点'
}

function startersForGame(game) {
  const text = `${game?.genre || ''} ${game?.world_type || ''} ${game?.title || ''}`
  const match = Object.entries(genreStarters).find(([keyword]) => text.includes(keyword))
  return match ? match[1] : defaultStarters
}

function withGameFlavor(character, game) {
  const genre = game?.genre || '自定义'
  const location = openingLocation(game)
  return {
    ...character,
    current_location: character.current_location || location,
    status: character.status || 'normal',
    affection_score: character.affection_score ?? 0,
    trust_score: character.trust_score ?? 0,
    tension_score: character.tension_score ?? 0,
    memory_summary: character.memory_summary || '故事刚开始，角色还没有长期记忆。',
    extra_attrs: JSON.stringify(
      {
        开场生成: true,
        题材参考: genre
      },
      null,
      2
    )
  }
}

export async function ensureStarterCharacters(gameId, game = null) {
  if (!gameId) return { created: false, characters: [] }
  const existing = await listCharacters(gameId)
  if (existing.length > 0) {
    return { created: false, characters: existing }
  }

  const createdCharacters = []
  for (const data of startersForGame(game)) {
    const character = await createCharacter(gameId, withGameFlavor(data, game))
    createdCharacters.push(character)
  }

  return { created: true, characters: createdCharacters }
}
