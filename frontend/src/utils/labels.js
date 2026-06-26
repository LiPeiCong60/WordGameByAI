export const roleTypeLabels = {
  protagonist: '主角',
  npc: 'NPC',
  villain: '反派',
  faction_representative: '阵营代表'
}

export const characterStatusLabels = {
  normal: '正常',
  alive: '存活',
  dead: '死亡',
  missing: '失踪',
  injured: '受伤',
  unknown: '未知'
}

export const ownerTypeLabels = {
  character: '角色',
  party: '队伍',
  location: '地点',
  faction: '阵营',
  story_world: '世界 / 副本',
  unknown: '未知'
}

export const itemStateLabels = {
  normal: '正常',
  damaged: '受损',
  broken: '损坏',
  lost: '丢失',
  hidden: '隐藏',
  consumed: '已消耗',
  equipped: '已装备',
  stored: '已存放',
  sealed: '已封印'
}

export const rarityLabels = {
  common: '普通',
  uncommon: '不常见',
  rare: '稀有',
  epic: '史诗',
  legendary: '传说',
  unique: '唯一',
  plot_item: '剧情道具'
}

export const canonLevelLabels = {
  hard_canon: '硬设定',
  soft_canon: '软设定',
  rumor: '传闻',
  deprecated: '废弃'
}

export const eventStatusLabels = {
  active: '进行中',
  resolved: '已解决',
  hidden: '隐藏',
  deprecated: '废弃'
}

export function labelFor(labels, value) {
  return labels[value] || value || '-'
}

export function optionsFrom(labels) {
  return Object.entries(labels).map(([value, label]) => ({ value, label }))
}
