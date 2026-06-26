export const characterPresets = [
  {
    label: '主角',
    data: {
      name: '主角',
      role_type: 'protagonist',
      gender: '自定义',
      age: '20',
      race_or_identity: '普通人 / 自定义身份',
      personality: '谨慎但有行动力，重视承诺。',
      speech_style: '自然、简洁，关键时刻坚定。',
      abilities: '观察、判断、基础体能。',
      status: 'normal',
      mood: '平静',
      current_goal: '了解当前处境，做出第一个关键选择。',
      memory_summary: '故事刚开始，主角还没有长期记忆。',
      agent_enabled: false,
      extra_attrs: '{}'
    }
  },
  {
    label: '重要 NPC',
    data: {
      name: '重要角色',
      role_type: 'npc',
      gender: '女',
      age: '22',
      race_or_identity: '重要同伴 / 自定义身份',
      personality: '细心、敏锐，对危险保持警觉。',
      speech_style: '温和但直接，会提醒主角风险。',
      abilities: '信息整理、情绪观察、基础应急处理。',
      status: 'normal',
      mood: '担忧但信任',
      relationship_to_player: '同伴',
      relationship_score: 50,
      current_goal: '协助主角完成当前目标，同时保护自己。',
      hidden_goal: '暂未公开。',
      memory_summary: '与主角刚建立基本信任。',
      agent_enabled: true,
      extra_attrs: '{}'
    }
  },
  {
    label: '反派',
    data: {
      name: '沈曜',
      role_type: 'villain',
      gender: '男',
      age: '未知',
      race_or_identity: '主要对手',
      personality: '冷静、强势，善于利用规则和人心。',
      speech_style: '克制、压迫感强，很少解释真实意图。',
      abilities: '资源调度、布局、谈判。',
      status: 'normal',
      mood: '从容',
      relationship_to_player: '敌对',
      relationship_score: -40,
      current_goal: '阻止主角接近核心真相。',
      hidden_goal: '隐藏真正动机。',
      agent_enabled: true,
      extra_attrs: '{}'
    }
  }
]

export const itemPresets = [
  {
    label: '消耗品',
    data: {
      name: '应急药剂',
      item_type: '消耗品',
      description: '用于处理轻伤或恢复少量体力。',
      is_consumable: true,
      is_stackable: true,
      quantity_limit: 20,
      usable_condition: '角色处于可行动状态。',
      effect_description: '缓解伤势或疲劳。',
      importance: 4
    }
  },
  {
    label: '装备',
    data: {
      name: '防护外套',
      item_type: '装备',
      description: '提供基础防护，适合日常探索。',
      is_equippable: true,
      is_stackable: false,
      quantity_limit: 1,
      effect_description: '降低轻微伤害风险。',
      importance: 5
    }
  },
  {
    label: '关键道具',
    data: {
      name: '旧钥匙',
      item_type: '关键道具',
      description: '能打开某个重要地点的门。',
      is_key_item: true,
      is_tradeable: false,
      is_unique: true,
      is_stackable: false,
      quantity_limit: 1,
      importance: 8,
      rarity: 'plot_item'
    }
  },
  {
    label: '情报',
    data: {
      name: '可疑名单',
      item_type: '情报',
      description: '记录了几个需要调查的人名。',
      is_key_item: true,
      is_tradeable: false,
      is_unique: true,
      is_stackable: false,
      quantity_limit: 1,
      importance: 7,
      rarity: 'rare'
    }
  }
]

export const eventPresets = [
  {
    label: '主线事件',
    data: {
      title: '第一条线索',
      event_type: '主线事件',
      arc_name: '开局',
      summary: '主角发现推动故事前进的第一条线索。',
      status: 'active',
      importance: 8,
      extra_attrs: '{}'
    }
  },
  {
    label: '关系事件',
    data: {
      title: '信任建立',
      event_type: '关系事件',
      arc_name: '人物关系',
      summary: '主角和重要 NPC 的关系发生明显变化。',
      status: 'active',
      importance: 6,
      extra_attrs: '{}'
    }
  },
  {
    label: '伏笔事件',
    data: {
      title: '未解释的异常',
      event_type: '伏笔事件',
      arc_name: '伏笔',
      summary: '出现一个暂时无法解释的异常，后续需要回收。',
      status: 'hidden',
      importance: 7,
      extra_attrs: '{}'
    }
  }
]
