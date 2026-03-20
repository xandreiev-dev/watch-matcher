<template>
  <div v-if="rows.length" class="table-wrapper">
    <h3>{{ title }}</h3>

    <table>
      <thead>
        <tr>
          <th>Название</th>
          <th>g_model_matched</th>
          <th>Бренд</th>
          <th>Модель</th>
          <th>Цвет</th>
          <th>Гарантия</th>
          <th>image_url</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="(row, index) in rows" :key="index">
          <td>{{ row["Название"] }}</td>
          <td>{{ row["g_model_matched"] }}</td>
          <td>{{ row["Бренд"] }}</td>
          <td>{{ row["Модель"] }}</td>
          <td>{{ row["Цвет"] }}</td>
          <td>{{ row["Гарантия"] }}</td>
          <td>
            <a v-if="row.image_url && row.URL" :href="row.URL" target="_blank">
              <img :src="row.image_url" alt="watch" class="thumb" />
            </a>
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
</style>