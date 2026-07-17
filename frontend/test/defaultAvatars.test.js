import assert from 'node:assert/strict'
import { access } from 'node:fs/promises'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { DEFAULT_AVATAR_PROFILES, matchDefaultAvatar } from '../src/utils/defaultAvatars.js'

const matchId = (character) => matchDefaultAvatar(character).id

test('默认头像目录覆盖 12 个年龄、性别和气质画像', () => {
  assert.equal(DEFAULT_AVATAR_PROFILES.length, 12)
  assert.equal(new Set(DEFAULT_AVATAR_PROFILES.map((profile) => profile.id)).size, 12)
})

test('按照性别、年龄和外貌标签匹配头像', () => {
  assert.equal(matchId({ name: '豆豆', gender: '男', age: '8岁', personality: '阳光活泼' }), 'child_boy_cheerful')
  assert.equal(matchId({ name: '小雨', gender: '女', age: '10', personality: '好奇文静' }), 'child_girl_curious')
  assert.equal(matchId({ name: '林川', gender: '男', age: '16', personality: '安静内向' }), 'teen_boy_quiet')
  assert.equal(matchId({ name: '夏晴', gender: '女', age: '17', personality: '活泼灵动' }), 'teen_girl_lively')
  assert.equal(matchId({ name: '程予安', gender: '男', age: '28', appearance: '英俊清秀，气质儒雅' }), 'young_man_refined')
  assert.equal(matchId({ name: '周野', gender: '男', age: '31', appearance: '粗犷强壮，脸上有疤' }), 'young_man_rugged')
  assert.equal(matchId({ name: '许晚', gender: '女', age: '26', appearance: '漂亮优雅' }), 'young_woman_elegant')
  assert.equal(matchId({ name: '陈姐', gender: '女', age: '48', personality: '成熟干练' }), 'middle_woman_capable')
  assert.equal(matchId({ name: '陈爷爷', gender: '男', age: '72', personality: '睿智慈祥' }), 'senior_man_wise')
})

test('90后不会被错误识别为 90 岁老人', () => {
  assert.match(matchId({ name: '阿杰', gender: '男', age: '90后', appearance: '帅气' }), /^young_man_/)
})

test('信息不足时仍然为同一角色稳定匹配', () => {
  const character = { name: '未知旅人', role_type: 'npc' }
  assert.equal(matchId(character), matchId({ ...character }))
})

test('所有头像资源均已复制到网页 public 目录', async () => {
  await Promise.all(DEFAULT_AVATAR_PROFILES.map((profile) => {
    const relativePath = profile.assetPath.replace(/^\//, '')
    return access(fileURLToPath(new URL(`../public/${relativePath}`, import.meta.url)))
  }))
})
