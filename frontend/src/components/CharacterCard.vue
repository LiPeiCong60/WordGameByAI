<template>
  <article class="character-card" role="button" tabindex="0" @keydown.enter="$event.currentTarget.click()">
    <CharacterAvatar
      class="character-card-avatar"
      :character="character"
      :avatar-url="character.avatar_url"
      :size="76"
      shape="rounded"
      show-auto-badge
    />
    <div class="card-body">
      <header>
        <h3>{{ character.name || '未命名角色' }}</h3>
        <span class="pill">{{ labelFor(roleTypeLabels, character.role_type) }}</span>
      </header>
      <div class="character-tags">
        <span v-if="character.gender">{{ character.gender }}</span>
        <span v-if="character.age">{{ character.age }}</span>
        <span v-if="character.race_or_identity">{{ character.race_or_identity }}</span>
      </div>
      <dl>
        <div><dt>状态</dt><dd>{{ labelFor(characterStatusLabels, character.status) }}</dd></div>
        <div><dt>心情</dt><dd>{{ character.mood || '-' }}</dd></div>
        <div><dt>位置</dt><dd>{{ character.current_location || '-' }}</dd></div>
        <div><dt>关系</dt><dd>{{ character.relationship_to_player || '-' }} · {{ character.relationship_score ?? 0 }}</dd></div>
        <div><dt>好感</dt><dd>{{ character.affection_score ?? 0 }}</dd></div>
        <div><dt>信任</dt><dd>{{ character.trust_score ?? 0 }}</dd></div>
        <div><dt>张力</dt><dd>{{ character.tension_score ?? 0 }}</dd></div>
      </dl>
      <p v-if="character.abilities">{{ character.abilities }}</p>
    </div>
  </article>
</template>

<script setup>
import CharacterAvatar from './CharacterAvatar.vue'
import { characterStatusLabels, labelFor, roleTypeLabels } from '../utils/labels'

const props = defineProps({
  character: { type: Object, required: true }
})
</script>
