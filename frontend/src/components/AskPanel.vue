<script setup>
import { onMounted, ref } from 'vue'
import { ask } from '../api'

const HISTORY_KEY = 'second-brain-ask-history'
const MAX_HISTORY = 50

const question = ref('')
const loading = ref(false)
const error = ref('')
const answer = ref('')
const sources = ref([])
const asked = ref(false)
const history = ref([])

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    history.value = raw ? JSON.parse(raw) : []
  } catch {
    history.value = []
  }
}

function saveHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
  } catch {
    // localStorage unavailable (private browsing, quota, etc.) — history just
    // won't persist across reloads, not worth surfacing as an error to the user.
  }
}

async function submit() {
  if (!question.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const result = await ask(question.value)
    answer.value = result.answer
    sources.value = result.sources
    asked.value = true

    history.value.unshift({
      question: question.value,
      answer: result.answer,
      sources: result.sources,
      askedAt: new Date().toISOString(),
    })
    history.value = history.value.slice(0, MAX_HISTORY)
    saveHistory()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function clearAnswer() {
  question.value = ''
  answer.value = ''
  sources.value = []
  error.value = ''
  asked.value = false
}

onMounted(loadHistory)
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" md="8">
      <v-form @submit.prevent="submit" class="d-flex align-center ga-2">
        <v-text-field
          v-model="question"
          label="Ask a question about your notes"
          append-inner-icon="mdi-send"
          @click:append-inner="submit"
          :loading="loading"
        ></v-text-field>
        <v-btn
          v-if="question || asked"
          variant="outlined"
          @click="clearAnswer"
        >
          Clear
        </v-btn>
      </v-form>

      <v-alert v-if="error" type="error" density="compact" class="mb-3">{{ error }}</v-alert>

      <v-card v-if="asked && !loading" class="mb-2" variant="outlined">
        <v-card-title>Answer</v-card-title>
        <v-card-text>{{ answer }}</v-card-text>
      </v-card>

      <div v-if="sources.length" class="mb-6">
        <h3 class="text-subtitle-1 mb-2">Sources</h3>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel v-for="(source, i) in sources" :key="i" :title="source.title">
            <v-expansion-panel-text>{{ source.chunk_text }}</v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>

      <div v-if="history.length">
        <h3 class="text-subtitle-1 mb-2">Past searches</h3>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel v-for="(entry, i) in history" :key="i" :title="entry.question">
            <v-expansion-panel-text>
              <p class="mb-3">{{ entry.answer }}</p>
              <div v-if="entry.sources.length">
                <div class="text-caption text-medium-emphasis mb-1">Sources</div>
                <v-chip
                  v-for="(source, j) in entry.sources"
                  :key="j"
                  size="small"
                  class="mr-1 mb-1"
                >
                  {{ source.title }}
                </v-chip>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>
    </v-col>
  </v-row>
</template>
