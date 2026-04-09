<template>
  <div v-if="rows.length" class="table-wrapper">
    <h3>{{ title }}</h3>

    <table>
      <thead>
        <tr>
          <th>Название</th>
          <th>match_status</th>
          <th>matched_model_name</th>
          <th>matched_model_id</th>
          <th>Бренд</th>
          <th>Модель</th>
          <th>Цвет</th>
          <th>Гарантия</th>
          <th>image_url</th>
        </tr>
      </thead>

      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="index"
          :class="getRowClass(row)"
        >
          <td>{{ row["Название"] || "—" }}</td>
          <td>
            <span :class="getStatusBadgeClass(row)">
              {{ getStatusText(row) }}
            </span>
          </td>
          <td>{{ row["matched_model_name"] || "—" }}</td>
          <td>{{ row["matched_model_id"] ?? "—" }}</td>
          <td>{{ row["Бренд"] || "—" }}</td>
          <td>{{ row["Модель"] || "—" }}</td>
          <td>{{ row["Цвет"] || "—" }}</td>
          <td>{{ row["Гарантия"] || "—" }}</td>
          <td>
            <a
              v-if="getImageUrl(row) && row.URL"
              :href="row.URL"
              target="_blank"
              rel="noopener noreferrer"
            >
              <img :src="getImageUrl(row)" alt="watch" class="thumb" />
            </a>

            <img
              v-else-if="getImageUrl(row)"
              :src="getImageUrl(row)"
              alt="watch"
              class="thumb"
            />

            <span v-else>—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
  title: {
    type: String,
    default: "Results",
  },
});

function isMatched(row) {
  return row?.match_status === "matched";
}

function getRowClass(row) {
  return isMatched(row) ? "row-matched" : "row-unmatched";
}

function getStatusText(row) {
  return row?.match_status || "unknown";
}

function getStatusBadgeClass(row) {
  return isMatched(row) ? "status-badge status-matched" : "status-badge status-unmatched";
}

function getImageUrl(row) {
  return row?.image_url || row?.img_url || "";
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const num = Number(value);

  if (Number.isNaN(num)) {
    return value;
  }

  return num.toFixed(3);
}
</script>

<style scoped>
.table-wrapper {
  overflow-x: auto;
  background: white;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #ddd;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th,
td {
  border: 1px solid #e5e7eb;
  padding: 10px;
  text-align: left;
  vertical-align: top;
}

th {
  background: #f3f4f6;
}

.thumb {
  width: 60px;
  height: auto;
  border-radius: 8px;
  display: block;
}

.row-matched {
  background-color: #f0fdf4;
}

.row-unmatched {
  background-color: #fef2f2;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-matched {
  background-color: #dcfce7;
  color: #66b083;
}

.status-unmatched {
  background-color: #fee2e2;
  color: #a85959;
}
</style>