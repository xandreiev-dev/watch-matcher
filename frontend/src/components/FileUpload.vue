<template>
  <div class="upload-box">
    <h2>Watch Matcher</h2>

    <div class="field">
      <label>Выбери XLSX файл:</label>
      <input type="file" accept=".xlsx" @change="handleFileChange" />
    </div>

    <div class="field">
      <label>Или вставь ссылку на XLSX:</label>
      <input
        type="text"
        v-model="fileUrl"
        placeholder="https://example.com/file.xlsx"
        class="url-input"
      />
    </div>

    <div class="buttons">
      <button :disabled="loading" @click="handleProcess">
        Обработать
      </button>
    </div>

    <p v-if="selectedFile">Selected file: {{ selectedFile.name }}</p>
    <p v-if="loading">Loading...</p>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { processFull } from "../services/api";

const emit = defineEmits(["processLoaded"]);

const selectedFile = ref(null);
const fileUrl = ref("");
const loading = ref(false);
const error = ref("");

function handleFileChange(event) {
  selectedFile.value = event.target.files[0] || null;
  error.value = "";
}

async function handleProcess() {
  const hasFile = !!selectedFile.value;
  const hasUrl = fileUrl.value.trim() !== "";

  if (!hasFile && !hasUrl) {
    error.value = "Выберите файл или вставьте ссылку на XLSX";
    return;
  }

  if (hasFile && hasUrl) {
    error.value = "Укажите что-то одно: либо файл, либо ссылку";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const data = await processFull(selectedFile.value, fileUrl.value);
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

.field {
  margin-bottom: 14px;
}

label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}

.url-input {
  width: 100%;
  max-width: 700px;
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
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