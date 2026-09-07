<script setup>
import { ref } from 'vue'
import { ingestText, ingestUrl, ingestFile } from '../api'
import ItemsList from './ItemsList.vue'

const subTab = ref('text')
const itemsList = ref(null)

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

function notify(text, color = 'success') {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

// Text form
const textForm = ref({ title: '', content: '', tags: '' })
const textLoading = ref(false)

async function submitText() {
  textLoading.value = true
  try {
    await ingestText(textForm.value)
    notify('Text ingested successfully.')
    textForm.value = { title: '', content: '', tags: '' }
    itemsList.value?.refresh()
  } catch (err) {
    notify(err.message, 'error')
  } finally {
    textLoading.value = false
  }
}

// URL form
const urlForm = ref({ url: '', title: '', tags: '' })
const urlLoading = ref(false)

async function submitUrl() {
  urlLoading.value = true
  try {
    await ingestUrl(urlForm.value)
    notify('URL ingested successfully.')
    urlForm.value = { url: '', title: '', tags: '' }
    itemsList.value?.refresh()
  } catch (err) {
    notify(err.message, 'error')
  } finally {
    urlLoading.value = false
  }
}

// File form
const fileForm = ref({ file: null, title: '', tags: '' })
const fileLoading = ref(false)

async function submitFile() {
  // v-file-input's v-model can be a File or a File[] depending on Vuetify version
  const picked = Array.isArray(fileForm.value.file) ? fileForm.value.file[0] : fileForm.value.file
  if (!picked) {
    notify('Choose a file first.', 'error')
    return
  }
  fileLoading.value = true
  try {
    await ingestFile({ file: picked, title: fileForm.value.title, tags: fileForm.value.tags })
    notify('File ingested successfully.')
    fileForm.value = { file: null, title: '', tags: '' }
    itemsList.value?.refresh()
  } catch (err) {
    notify(err.message, 'error')
  } finally {
    fileLoading.value = false
  }
}
</script>

<template>
  <v-row>
    <v-col cols="12" md="6">
      <v-card variant="outlined">
        <v-tabs v-model="subTab" color="primary">
          <v-tab value="text">Text</v-tab>
          <v-tab value="url">URL</v-tab>
          <v-tab value="file">File</v-tab>
        </v-tabs>

        <v-card-text>
          <v-window v-model="subTab">
            <v-window-item value="text">
              <v-form @submit.prevent="submitText">
                <v-text-field v-model="textForm.title" label="Title" required></v-text-field>
                <v-textarea v-model="textForm.content" label="Content" rows="6" required></v-textarea>
                <v-text-field v-model="textForm.tags" label="Tags (optional)"></v-text-field>
                <v-btn type="submit" color="primary" :loading="textLoading">Ingest text</v-btn>
              </v-form>
            </v-window-item>

            <v-window-item value="url">
              <v-form @submit.prevent="submitUrl">
                <v-text-field v-model="urlForm.url" label="URL" required></v-text-field>
                <v-text-field v-model="urlForm.title" label="Title (optional)"></v-text-field>
                <v-text-field v-model="urlForm.tags" label="Tags (optional)"></v-text-field>
                <v-btn type="submit" color="primary" :loading="urlLoading">Ingest URL</v-btn>
              </v-form>
            </v-window-item>

            <v-window-item value="file">
              <v-form @submit.prevent="submitFile">
                <v-file-input
                  v-model="fileForm.file"
                  label="File (.pdf, .txt, .md, .docx)"
                  accept=".pdf,.txt,.md,.docx"
                  required
                ></v-file-input>
                <v-text-field v-model="fileForm.title" label="Title (optional)"></v-text-field>
                <v-text-field v-model="fileForm.tags" label="Tags (optional)"></v-text-field>
                <v-btn type="submit" color="primary" :loading="fileLoading">Ingest file</v-btn>
              </v-form>
            </v-window-item>
          </v-window>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" md="6">
      <ItemsList ref="itemsList" />
    </v-col>
  </v-row>

  <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="4000">
    {{ snackbarText }}
  </v-snackbar>
</template>
