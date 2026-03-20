<template>
  <div class="container">
    <FileUpload @processLoaded="handleProcessLoaded" />

    <ResultsTable
      v-if="processedRows.length"
      :rows="processedRows"
      title="Результат обработки"
    />
  </div>
</template>

<script setup>
import { ref } from "vue";
import FileUpload from "./components/FileUpload.vue";
import ResultsTable from "./components/ResultsTable.vue";

const processedRows = ref([]);

function handleProcessLoaded(data) {
  processedRows.value = data.data || [];
}
</script>

<style>
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: #f9fafb;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}
</style>