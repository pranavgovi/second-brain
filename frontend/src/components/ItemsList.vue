<script setup>
import { onMounted, ref, defineExpose } from 'vue'
import { listIngested } from '../api'

const items = ref([])
const loading = ref(false)
const error = ref('')

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    items.value = await listIngested()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function preview(content) {
  if (!content) return '(no extracted content)'
  return content.length > 160 ? content.slice(0, 160) + '…' : content
}

onMounted(refresh)
defineExpose({ refresh })
</script>

<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-2">
      <h3 class="text-h6">Ingested items</h3>
      <v-btn size="small" variant="text" icon="mdi-refresh" @click="refresh" :loading="loading"></v-btn>
    </div>

    <v-alert v-if="error" type="error" density="compact" class="mb-3">{{ error }}</v-alert>

    <v-alert v-if="!loading && items.length === 0" type="info" density="compact">
      Nothing ingested yet.
    </v-alert>

    <v-card v-for="item in items" :key="item.id" class="mb-2" variant="outlined">
      <v-card-item>
        <v-card-title>{{ item.title }}</v-card-title>
        <v-card-subtitle>
          <v-chip size="x-small" class="mr-2">{{ item.source_type }}</v-chip>
          <span v-if="item.tags">{{ item.tags }}</span>
        </v-card-subtitle>
      </v-card-item>
      <v-card-text>{{ preview(item.content) }}</v-card-text>
    </v-card>
  </div>
</template>
