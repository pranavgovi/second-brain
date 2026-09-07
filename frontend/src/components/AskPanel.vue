<script setup>
import { ref } from 'vue'
import { ask } from '../api'

const question = ref('')
const loading = ref(false)
const error = ref('')
const answer = ref('')
const sources = ref([])
const asked = ref(false)

async function submit() {
  if (!question.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const result = await ask(question.value)
    answer.value = result.answer
    sources.value = result.sources
    asked.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" md="8">
      <v-form @submit.prevent="submit">
        <v-text-field
          v-model="question"
          label="Ask a question about your notes"
          append-inner-icon="mdi-send"
          @click:append-inner="submit"
          :loading="loading"
        ></v-text-field>
      </v-form>

      <v-alert v-if="error" type="error" density="compact" class="mb-3">{{ error }}</v-alert>

      <v-card v-if="asked && !loading" class="mb-4" variant="outlined">
        <v-card-title>Answer</v-card-title>
        <v-card-text>{{ answer }}</v-card-text>
      </v-card>

      <div v-if="sources.length">
        <h3 class="text-subtitle-1 mb-2">Sources</h3>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel v-for="(source, i) in sources" :key="i" :title="source.title">
            <v-expansion-panel-text>{{ source.chunk_text }}</v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>
    </v-col>
  </v-row>
</template>
