<template>
  <div class="container">
    <FileUpload
      @previewLoaded="handlePreviewLoaded"
      @processLoaded="handleProcessLoaded"
    />

    <ResultsTable
      v-if="previewRows.length"
      :rows="previewRows"
      title="Excel Preview"
    />

    <ResultsTable
      v-if="processedRows.length"
      :rows="processedRows"
      title="Processed Results"
    />
  </div>
</template>

<script setup>
import { ref } from "vue";
import FileUpload from "./components/FileUpload.vue";
import ResultsTable from "./components/ResultsTable.vue";

const previewRows = ref([]);
const processedRows = ref([]);

function handlePreviewLoaded(data) {
  previewRows.value = data.preview || [];
  processedRows.value = [];
}

function handleProcessLoaded(data) {
  previewRows.value = [];
  processedRows.value = data.preview || data.data || [];
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