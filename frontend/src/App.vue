<script setup>
import { ref } from 'vue'
import IngestPanel from './components/IngestPanel.vue'
import AskPanel from './components/AskPanel.vue'

const tab = ref('ingest')
</script>

<template>
  <v-app>
    <v-app-bar color="primary">
      <v-app-bar-title>Second Brain</v-app-bar-title>
    </v-app-bar>

    <v-main>
      <v-container>
        <v-tabs v-model="tab" color="primary" class="mb-4">
          <v-tab value="ingest">Ingest</v-tab>
          <v-tab value="ask">Ask</v-tab>
        </v-tabs>

        <v-window v-model="tab">
          <v-window-item value="ingest">
            <IngestPanel />
          </v-window-item>
          <v-window-item value="ask">
            <AskPanel />
          </v-window-item>
        </v-window>
      </v-container>
    </v-main>
  </v-app>
</template>
