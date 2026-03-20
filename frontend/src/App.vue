<template>
  <div class="container">
    <FileUpload @processLoaded="handleProcessLoaded" />

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
          Экспорт в Excel
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

function exportToExcel() {
  if (!filteredRows.value.length) return;

  const headers = [
    "Название",
    "g_model_matched",
    "Бренд",
    "Модель",
    "Цвет",
    "Гарантия",
    "URL",
    "image_url",
  ];

  const csvRows = [
    headers.join(","),
    ...filteredRows.value.map((row) =>
      headers
        .map((header) => {
          const value = row[header] ?? "";
          const escaped = String(value).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(",")
    ),
  ];

  const csvContent = "\uFEFF" + csvRows.join("\n");
  const blob = new Blob([csvContent], {
    type: "text/csv;charset=utf-8;",
  });

  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute("download", "watch_matcher_results.csv");
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
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

.empty-state {
  padding: 18px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 12px;
}
</style>