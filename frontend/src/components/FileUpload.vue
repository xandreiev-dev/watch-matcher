<template>
  <div class="upload-box">
    <h2>Watch Matcher</h2>

    <input type="file" accept=".xlsx" @change="handleFileChange" />

    <div class="buttons">
      <button :disabled="!selectedFile || loading" @click="handlePreview">
        Preview Excel
      </button>

      <button :disabled="!selectedFile || loading" @click="handleProcessPreview">
        Process Preview
      </button>

      <button :disabled="!selectedFile || loading" @click="handleProcessFull">
        Process Full File
      </button>
    </div>

    <p v-if="selectedFile">Selected file: {{ selectedFile.name }}</p>
    <p v-if="loading">Loading...</p>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { uploadPreview, processPreview, processFull } from "../services/api";

const emit = defineEmits(["previewLoaded", "processLoaded"]);

const selectedFile = ref(null);
const loading = ref(false);
const error = ref("");

function handleFileChange(event) {
  selectedFile.value = event.target.files[0] || null;
  error.value = "";
}

async function handlePreview() {
  if (!selectedFile.value) return;

  loading.value = true;
  error.value = "";

  try {
    const data = await uploadPreview(selectedFile.value);
    emit("previewLoaded", data);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function handleProcessPreview() {
  if (!selectedFile.value) return;

  loading.value = true;
  error.value = "";

  try {
    const data = await processPreview(selectedFile.value);
    emit("processLoaded", data);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function handleProcessFull() {
  if (!selectedFile.value) return;

  loading.value = true;
  error.value = "";

  try {
    const data = await processFull(selectedFile.value);
    emit("processLoaded", data);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.upload-box {
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 12px;
  margin-bottom: 20px;
  background: #fff;
}

.buttons {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

button {
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: #111827;
  color: white;
}

button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.error {
  color: #dc2626;
}
</style>