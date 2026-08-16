<template>
  <div class="container">
    <FileUpload @processLoaded="handleProcessLoaded" />

    <section v-if="processedRows.length" class="summary-bar">
      <div class="metric">
        <span>Total</span>
        <strong>{{ totalRows }}</strong>
      </div>
      <div class="metric">
        <span>Matched</span>
        <strong>{{ matchedRows }}</strong>
      </div>
      <div class="metric">
        <span>Unmatched</span>
        <strong>{{ unmatchedRows }}</strong>
      </div>
      <div class="metric">
        <span>Review</span>
        <strong>{{ reviewRows }}</strong>
      </div>
      <div class="metric">
        <span>Avg confidence</span>
        <strong>{{ averageConfidence }}</strong>
      </div>
    </section>

    <section v-if="processedRows.length" class="toolbar">
      <label class="toolbar-field search-field">
        <span>Search</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="title, model, article, url"
          class="toolbar-input"
        />
      </label>

      <label class="toolbar-field">
        <span>Source</span>
        <select v-model="sourceFilter" class="toolbar-select">
          <option value="all">All</option>
          <option v-for="source in sourceOptions" :key="source" :value="source">
            {{ source }}
          </option>
        </select>
      </label>

      <label class="toolbar-field">
        <span>Brand</span>
        <select v-model="brandFilter" class="toolbar-select">
          <option value="all">All</option>
          <option v-for="brand in brandOptions" :key="brand" :value="brand">
            {{ brand }}
          </option>
        </select>
      </label>

      <label class="toolbar-field">
        <span>Status</span>
        <select v-model="statusFilter" class="toolbar-select">
          <option value="all">All</option>
          <option v-for="status in statusOptions" :key="status" :value="status">
            {{ status }}
          </option>
        </select>
      </label>

      <div class="export-actions">
        <button @click="exportFullToExcel">Full</button>
        <button @click="exportMatchedToExcel">Matched</button>
        <button @click="exportUnmatchedToExcel">Unmatched</button>
        <button @click="exportReviewToExcel">Review</button>
      </div>
    </section>

    <ResultsTable
      v-if="filteredRows.length"
      :rows="filteredRows"
      title="Matching Results"
    />

    <p v-else-if="processedRows.length" class="empty-state">
      По текущим фильтрам ничего не найдено.
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
const sourceFilter = ref("all");
const brandFilter = ref("all");
const statusFilter = ref("all");

function handleProcessLoaded(payload) {
  const rows = payload?.data || payload?.preview || [];
  processedRows.value = rows.map((row) => ({
    ...row,
    source: row?.source || payload?.source,
    shop_id: row?.shop_id ?? payload?.shop_id,
  }));
  searchQuery.value = "";
  sourceFilter.value = "all";
  brandFilter.value = "all";
  statusFilter.value = "all";
}

function getBrand(row) {
  return row?.brand || row?.["Бренд"] || "—";
}

function getSource(row) {
  return row?.source || (Number(row?.shop_id) === 1 ? "ozon" : Number(row?.shop_id) === 2 ? "avito" : "—");
}

function isMatched(row) {
  return row?.match_status === "matched";
}

function needsManualReview(row) {
  return row?.needs_manual_review === true || row?.needs_manual_review === "true" || row?.needs_manual_review === 1;
}

function uniqueSorted(values) {
  return [...new Set(values.filter((value) => value && value !== "—"))].sort((a, b) =>
    String(a).localeCompare(String(b), "ru")
  );
}

const totalRows = computed(() => processedRows.value.length);

const matchedRows = computed(() => processedRows.value.filter(isMatched).length);

const unmatchedRows = computed(() => processedRows.value.filter((row) => !isMatched(row)).length);

const reviewRows = computed(() => processedRows.value.filter(needsManualReview).length);

const averageConfidence = computed(() => {
  const values = processedRows.value
    .map((row) => Number(row?.confidence))
    .filter((value) => Number.isFinite(value));

  if (!values.length) return "—";

  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
  return avg.toFixed(2);
});

const sourceOptions = computed(() => uniqueSorted(processedRows.value.map(getSource)));

const brandOptions = computed(() => uniqueSorted(processedRows.value.map(getBrand)));

const statusOptions = computed(() =>
  uniqueSorted(processedRows.value.map((row) => row?.match_status || "unknown"))
);

const filteredRows = computed(() => {
  let rows = [...processedRows.value];

  if (sourceFilter.value !== "all") {
    rows = rows.filter((row) => getSource(row) === sourceFilter.value);
  }

  if (brandFilter.value !== "all") {
    rows = rows.filter((row) => getBrand(row) === brandFilter.value);
  }

  if (statusFilter.value !== "all") {
    rows = rows.filter((row) => (row?.match_status || "unknown") === statusFilter.value);
  }

  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return rows;

  return rows.filter((row) => {
    const haystack = [
      row?.["Название"],
      row?.product_name,
      row?.title,
      row?.brand,
      row?.["Бренд"],
      row?.model,
      row?.display_model,
      row?.family,
      row?.generation,
      row?.variant,
      row?.matched_model_name,
      row?.matched_variant_name,
      row?.article,
      row?.URL,
      row?.product_url,
    ]
      .filter((value) => value !== null && value !== undefined)
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
});

function normalizeRowForExport(row) {
  return {
    shop_id: getShopId(row),
    source: getSource(row),
    brand: getBrand(row),
    model: row?.model || row?.display_model || row?.matched_model_name || "",
    variant: row?.variant || row?.matched_variant_name || row?.extracted_variant_name || "",
    price: row?.price ?? "",
    image_url: row?.image_url || row?.img_url || "",
    match_status: row?.match_status || "",
    matched_model_name: row?.matched_model_name || "",
    matched_variant_name: row?.matched_variant_name || "",
    case_size_mm: row?.case_size_mm ?? row?.size_mm ?? "",
    delivery_days: getDeliveryDays(row),
    warranty: row?.["Гарантия"] || row?.warranty || row?.warranty_period || "",
    title: row?.["Название"] || row?.product_name || "",
    article: row?.article ?? "",
    url: row?.URL || row?.product_url || "",
    confidence: row?.confidence ?? "",
    matched_model_id: row?.matched_model_id ?? "",
    matched_variant_id: row?.matched_variant_id ?? "",
    needs_manual_review: row?.needs_manual_review ?? "",
  };
}

function exportRowsToExcel(rows, filename) {
  if (!rows.length) return;

  const worksheet = XLSX.utils.json_to_sheet(rows.map(normalizeRowForExport));
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Results");
  XLSX.writeFile(workbook, filename);
}

function exportFullToExcel() {
  exportRowsToExcel(processedRows.value, "watch_matcher_full.xlsx");
}

function exportMatchedToExcel() {
  exportRowsToExcel(processedRows.value.filter(isMatched), "watch_matcher_matched.xlsx");
}

function exportUnmatchedToExcel() {
  exportRowsToExcel(processedRows.value.filter((row) => !isMatched(row)), "watch_matcher_unmatched.xlsx");
}

function getShopId(row) {
  if (row?.shop_id !== null && row?.shop_id !== undefined && row?.shop_id !== "") {
    return row.shop_id;
  }

  const source = getSource(row);
  if (source === "ozon") return 1;
  if (source === "avito") return 2;

  return "";
}

function getDeliveryDays(row) {
  const value = row?.delivery_days ?? row?.days_to_delivery;
  if (value === null || value === undefined || value === "") return "";

  const text = String(value).trim();
  if (!/^\d+([.,]\d+)?$/.test(text) && !/(день|дня|дней|day|days)/i.test(text)) {
    return "";
  }

  const match = text.match(/\d+([.,]\d+)?/);
  return match ? Math.round(Number(match[0].replace(",", "."))) : "";
}

function exportReviewToExcel() {
  exportRowsToExcel(processedRows.value.filter(needsManualReview), "watch_matcher_review.xlsx");
}
</script>

<style>
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: #f6f7f9;
  color: #111827;
}

.container {
  max-width: 1500px;
  margin: 0 auto;
  padding: 20px;
}

.summary-bar {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 1px;
  margin-bottom: 14px;
  overflow: hidden;
  border: 1px solid #d9dde3;
  border-radius: 8px;
  background: #d9dde3;
}

.metric {
  min-width: 0;
  padding: 12px 14px;
  background: #fff;
}

.metric span {
  display: block;
  margin-bottom: 4px;
  color: #667085;
  font-size: 12px;
}

.metric strong {
  font-size: 18px;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) 150px 180px 190px auto;
  gap: 10px;
  align-items: end;
  margin-bottom: 14px;
  padding: 12px;
  background: white;
  border: 1px solid #d9dde3;
  border-radius: 8px;
}

.toolbar-field {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 5px;
  font-size: 12px;
  color: #667085;
}

.toolbar-input,
.toolbar-select {
  height: 36px;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid #cfd5df;
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
  color: #111827;
}

.export-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.export-actions button {
  height: 36px;
  padding: 0 12px;
  border: none;
  border-radius: 6px;
  background: #111827;
  color: white;
  cursor: pointer;
}

.export-actions button:hover {
  background: #273244;
}

.empty-state {
  padding: 18px;
  background: white;
  border: 1px solid #d9dde3;
  border-radius: 8px;
}

@media (max-width: 900px) {
  .summary-bar {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }

  .toolbar {
    grid-template-columns: 1fr;
  }

  .export-actions {
    justify-content: flex-start;
  }
}
</style>
