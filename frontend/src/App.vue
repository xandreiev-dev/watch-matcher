<template>
  <div class="container">
    <FileUpload @processLoaded="handleProcessLoaded" />

    <div v-if="processedRows.length" class="stats-bar">
      <div class="stats-text">
        <strong>Статистика:</strong>
        всего {{ totalRows }} · совпало {{ matchedRows }} · не совпало {{ unmatchedRows }}
      </div>

      <div class="stats-actions">
        <button @click="exportMatchedToExcel" class="export-btn green-btn">
          Скачать matched.xlsx
        </button>
        <button @click="exportUnmatchedToExcel" class="export-btn green-btn">
          Скачать unmatched.xlsx
        </button>
      </div>
    </div>

    <div v-if="processedRows.length" class="toolbar">
      <div class="toolbar-group">
        <label for="search">Поиск:</label>
        <input
          id="search"
          v-model="searchQuery"
          type="text"
          placeholder="Поиск по названию, бренду, модели..."
          class="toolbar-input"
        />
      </div>

      <div class="toolbar-group">
        <label for="filter">Фильтр:</label>
        <select id="filter" v-model="filterMode" class="toolbar-select">
          <option value="all">Все</option>
          <option value="matched">Только matched</option>
          <option value="unmatched">Только unmatched</option>
        </select>
      </div>

      <div class="toolbar-group">
        <button @click="exportToExcel" class="export-btn">
          Экспорт текущего вида в Excel
        </button>
      </div>
    </div>

    <ResultsTable
      v-if="filteredRows.length"
      :rows="filteredRows"
      title="Результат обработки"
    />

    <p v-else-if="processedRows.length" class="empty-state">
      По текущему фильтру ничего не найдено.
    </p>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import * as XLSX from "xlsx";
import FileUpload from "./components/FileUpload.vue";
import ResultsTable from "./components/ResultsTable.vue";

const processedRows = ref([]);
const searchQuery = ref("");
const filterMode = ref("all");

function handleProcessLoaded(data) {
  processedRows.value = data.data || [];
  searchQuery.value = "";
  filterMode.value = "all";
}

const totalRows = computed(() => processedRows.value.length);

const matchedRows = computed(() =>
  processedRows.value.filter(
    (row) =>
      row["g_model_matched"] &&
      row["g_model_matched"] !== "Unknown"
  ).length
);

const unmatchedRows = computed(() =>
  processedRows.value.filter(
    (row) =>
      !row["g_model_matched"] ||
      row["g_model_matched"] === "Unknown"
  ).length
);

const filteredRows = computed(() => {
  let rows = [...processedRows.value];

  if (filterMode.value === "matched") {
    rows = rows.filter(
      (row) =>
        row["g_model_matched"] &&
        row["g_model_matched"] !== "Unknown"
    );
  }

  if (filterMode.value === "unmatched") {
    rows = rows.filter(
      (row) =>
        !row["g_model_matched"] ||
        row["g_model_matched"] === "Unknown"
    );
  }

  const query = searchQuery.value.trim().toLowerCase();

  if (!query) {
    return rows;
  }

  return rows.filter((row) => {
    const haystack = [
      row["Название"] || "",
      row["Бренд"] || "",
      row["Модель"] || "",
      row["g_model_matched"] || "",
      row["Цвет"] || "",
      row["Гарантия"] || "",
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
});

function exportRowsToExcel(rows, filename) {
  if (!rows.length) return;

  const exportRows = rows.map((row) => ({
    "Название": row["Название"] ?? "",
    "g_model_matched": row["g_model_matched"] ?? "",
    "Бренд": row["Бренд"] ?? "",
    "Модель": row["Модель"] ?? "",
    "Цвет": row["Цвет"] ?? "",
    "Гарантия": row["Гарантия"] ?? "",
    "URL": row["URL"] ?? "",
    "image_url": row["image_url"] ?? "",
  }));

  const worksheet = XLSX.utils.json_to_sheet(exportRows);
  const workbook = XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(workbook, worksheet, "Results");
  XLSX.writeFile(workbook, filename);
}

function exportToExcel() {
  exportRowsToExcel(filteredRows.value, "watch_matcher_results.xlsx");
}

function exportMatchedToExcel() {
  const matched = processedRows.value.filter(
    (row) =>
      row["g_model_matched"] &&
      row["g_model_matched"] !== "Unknown"
  );

  exportRowsToExcel(matched, "matched.xlsx");
}

function exportUnmatchedToExcel() {
  const unmatched = processedRows.value.filter(
    (row) =>
      !row["g_model_matched"] ||
      row["g_model_matched"] === "Unknown"
  );

  exportRowsToExcel(unmatched, "unmatched.xlsx");
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

.stats-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #0f172a;
  color: white;
  border-radius: 14px;
}

.stats-text {
  font-size: 16px;
}

.stats-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar {
  display: flex;
  gap: 16px;
  align-items: end;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding: 16px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 12px;
}

.toolbar-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toolbar-input,
.toolbar-select {
  padding: 10px;
  min-width: 240px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
}

.export-btn {
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: #111827;
  color: white;
}

.green-btn {
  background: #059669;
}

.green-btn:hover {
  background: #047857;
}

.empty-state {
  padding: 18px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 12px;
}
</style>