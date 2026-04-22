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

function handleProcessLoaded(payload) {
  processedRows.value = payload?.data || [];
  searchQuery.value = "";
  filterMode.value = "all";
}

function isMatched(row) {
  return row?.match_status === "matched";
}

function isUnmatched(row) {
  return row?.match_status !== "matched";
}

const totalRows = computed(() => processedRows.value.length);

const matchedRows = computed(() =>
  processedRows.value.filter((row) => isMatched(row)).length
);

const unmatchedRows = computed(() =>
  processedRows.value.filter((row) => isUnmatched(row)).length
);

const filteredRows = computed(() => {
  let rows = [...processedRows.value];

  if (filterMode.value === "matched") {
    rows = rows.filter((row) => isMatched(row));
  } else if (filterMode.value === "unmatched") {
    rows = rows.filter((row) => isUnmatched(row));
  }

  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return rows;

  return rows.filter((row) => {
    const haystack = [
      row["Название"] || "",
      row["Бренд"] || "",
      row["Модель"] || "",
      row["match_status"] || "",
      row["matched_model_name"] || "",
      row["matched_model_id"] ?? "",
      row["family"] || "",
      row["generation"] || "",
      row["variant"] || "",
      row["article"] || "",
      row["Цвет"] || "",
      row["Гарантия"] || "",
      row["URL"] || "",
      row["image_url"] || "",
      row["img_url"] || "",
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
});

function normalizeRowForExport(row) {
  const imageUrl = row["image_url"] || row["img_url"] || "";

  return {
    "Название": row["Название"] ?? "",
    "Бренд": row["Бренд"] ?? "",
    Модель: row.display_model ?? "",
    "article": row["article"] ?? "",
    "size_mm": row["size_mm"] ?? "",
    "family": row["family"] ?? "",
    "generation": row["generation"] ?? "",
    "variant": row["variant"] ?? "",
    "Цвет": row["Цвет"] ?? "",
    "Гарантия": row["Гарантия"] ?? "",
    "URL": row["URL"] ?? "",
    "image_url": imageUrl,
    "img_url": imageUrl,
    "match_status": row["match_status"] ?? "",
    "matched_model_id": row["matched_model_id"] ?? "",
    "matched_model_name": row["matched_model_name"] ?? "",
    "match_method": row["match_method"] ?? "",
    "needs_manual_review": row["needs_manual_review"] ?? "",
  };
}

function exportRowsToExcel(rows, filename) {
  if (!rows.length) return;

  const exportRows = rows.map(normalizeRowForExport);

  const worksheet = XLSX.utils.json_to_sheet(exportRows);
  const workbook = XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(workbook, worksheet, "Results");
  XLSX.writeFile(workbook, filename);
}

function exportToExcel() {
  exportRowsToExcel(filteredRows.value, "watch_matcher_results.xlsx");
}

function exportMatchedToExcel() {
  const matched = processedRows.value.filter((row) => isMatched(row));
  exportRowsToExcel(matched, "matched.xlsx");
}

function exportUnmatchedToExcel() {
  const unmatched = processedRows.value.filter((row) => isUnmatched(row));
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