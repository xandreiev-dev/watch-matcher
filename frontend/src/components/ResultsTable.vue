<template>
  <section class="results-panel">
    <div class="results-header">
      <h3>{{ title }}</h3>
      <span>{{ rows.length }} rows</span>
    </div>

    <div class="table-scroll">
      <table class="results-table">
        <thead>
          <tr>
            <th>shop_id</th>
            <th>source</th>
            <th>brand</th>
            <th>model</th>
            <th>variant</th>
            <th>price</th>
            <th>image</th>
            <th>status</th>
            <th>Matched model</th>
            <th>delivery</th>
            <th>warranty</th>
          </tr>
        </thead>

        <tbody>
          <template v-for="(row, index) in rows" :key="getRowKey(row, index)">
            <tr :class="getRowClass(row)" @click="toggleRow(index)">
              <td>{{ getShopId(row) }}</td>
              <td>{{ getSource(row) }}</td>
              <td>{{ getBrand(row) }}</td>
              <td>{{ getModel(row) }}</td>
              <td>{{ getVariant(row) }}</td>
              <td class="number-cell">{{ formatPrice(row.price) }}</td>
              <td class="image-cell">
                <a
                  v-if="getImageUrl(row)"
                  :href="getProductUrl(row) || getImageUrl(row)"
                  target="_blank"
                  rel="noopener noreferrer"
                  @click.stop
                >
                  <img :src="getImageUrl(row)" alt="" class="thumb" loading="lazy" />
                </a>
                <span v-else>—</span>
              </td>
              <td>
                <span :class="getStatusBadgeClass(row)">
                  {{ row.match_status || "unknown" }}
                </span>
              </td>
              <td class="matched-model">{{ getMatchedModel(row) }}</td>
              <td class="number-cell">{{ formatDelivery(row) }}</td>
              <td class="number-cell">{{ formatWarranty(row) }}</td>
            </tr>

            <tr v-if="expandedRow === index" class="details-row">
              <td colspan="11">
                <div class="details-grid">
                  <div class="details-main">
                    <h4>{{ getTitle(row) }}</h4>
                    <dl>
                      <div>
                        <dt>article</dt>
                        <dd>{{ row.article ?? "—" }}</dd>
                      </div>
                      <div>
                        <dt>url</dt>
                        <dd>
                          <a
                            v-if="getProductUrl(row)"
                            :href="getProductUrl(row)"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {{ getProductUrl(row) }}
                          </a>
                          <span v-else>—</span>
                        </dd>
                      </div>
                      <div>
                        <dt>rating</dt>
                        <dd>{{ getFirst(row, ["rating", "shop_rating", "Звезды"]) }}</dd>
                      </div>
                      <div>
                        <dt>reviews</dt>
                        <dd>{{ getFirst(row, ["review", "reviews", "reviews_count", "Отзывы"]) }}</dd>
                      </div>
                      <div>
                        <dt>old_price</dt>
                        <dd>{{ getFirst(row, ["old_price", "Price"]) }}</dd>
                      </div>
                      <div>
                        <dt>discount_price</dt>
                        <dd>{{ getFirst(row, ["discount_price", "Discount Price", "price"]) }}</dd>
                      </div>
                      <div>
                        <dt>delivery raw</dt>
                        <dd>{{ getFirst(row, ["delivery_raw", "delivery_date", "Доставка", "days_to_delivery"]) }}</dd>
                      </div>
                      <div>
                        <dt>characteristics</dt>
                        <dd>{{ getFirst(row, ["characteristics", "Описание"]) }}</dd>
                      </div>
                      <div>
                        <dt>confidence</dt>
                        <dd>{{ formatConfidence(row.confidence) }}</dd>
                      </div>
                      <div>
                        <dt>matched_model_id</dt>
                        <dd>{{ row.matched_model_id ?? "—" }}</dd>
                      </div>
                      <div>
                        <dt>matched_variant_id</dt>
                        <dd>{{ row.matched_variant_id ?? "—" }}</dd>
                      </div>
                      <div>
                        <dt>needs_manual_review</dt>
                        <dd>{{ row.needs_manual_review ?? "—" }}</dd>
                      </div>
                    </dl>
                  </div>

                  <details class="debug-box">
                    <summary>original row JSON / debug</summary>
                    <pre>{{ JSON.stringify(row, null, 2) }}</pre>
                  </details>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";

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

const expandedRow = ref(null);

function toggleRow(index) {
  expandedRow.value = expandedRow.value === index ? null : index;
}

function getRowKey(row, index) {
  return row?.article || row?.URL || row?.product_url || index;
}

function getSource(row) {
  return row?.source || (Number(row?.shop_id) === 1 ? "ozon" : Number(row?.shop_id) === 2 ? "avito" : "—");
}

function getShopId(row) {
  if (row?.shop_id !== null && row?.shop_id !== undefined && row?.shop_id !== "") {
    return row.shop_id;
  }

  const source = getSource(row);
  if (source === "ozon") return 1;
  if (source === "avito") return 2;

  return "—";
}

function getBrand(row) {
  return row?.brand || row?.["Бренд"] || "—";
}

function getModel(row) {
  const parts = [row?.family, row?.generation].filter(Boolean);
  return row?.model || row?.["Модель"] || (parts.length ? parts.join(" ") : row?.display_model) || "—";
}

function getVariant(row) {
  return row?.variant || row?.extracted_variant_name || "—";
}

function getTitle(row) {
  return row?.["Название"] || row?.product_name || row?.title || "—";
}

function getImageUrl(row) {
  return row?.image_url || row?.img_url || "";
}

function getProductUrl(row) {
  return row?.URL || row?.product_url || "";
}

function getMatchedModel(row) {
  const parts = [row?.matched_model_name, row?.matched_variant_name].filter(Boolean);
  const size = row?.case_size_mm ?? row?.size_mm;

  if (size !== null && size !== undefined && size !== "") {
    parts.push(`${size}mm`);
  }

  return parts.length ? parts.join(" · ") : "—";
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") return "—";

  const num = Number(value);
  if (!Number.isFinite(num)) return value;

  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 0,
  }).format(num);
}

function formatDelivery(row) {
  const value = row?.delivery_days ?? row?.days_to_delivery;
  if (value === null || value === undefined || value === "") return "—";

  const text = String(value).trim();
  if (!/^\d+([.,]\d+)?$/.test(text) && !/(день|дня|дней|day|days)/i.test(text)) {
    return "—";
  }

  const match = text.match(/\d+([.,]\d+)?/);
  const num = match ? Number(match[0].replace(",", ".")) : NaN;
  if (!Number.isFinite(num)) return value;

  return String(Math.round(num));
}

function formatWarranty(row) {
  const value = row?.["Гарантия"] ?? row?.warranty ?? row?.warranty_period;
  if (value === null || value === undefined || value === "") return "—";

  return value;
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === "") return "—";

  const num = Number(value);
  if (!Number.isFinite(num)) return value;

  return num.toFixed(3);
}

function getFirst(row, keys) {
  for (const key of keys) {
    const value = row?.[key];
    if (value !== null && value !== undefined && value !== "") {
      return value;
    }
  }

  return "—";
}

function isMatched(row) {
  return row?.match_status === "matched";
}

function needsManualReview(row) {
  return row?.needs_manual_review === true || row?.needs_manual_review === "true" || row?.needs_manual_review === 1;
}

function getRowClass(row) {
  if (isMatched(row)) return "row-matched";
  if (needsManualReview(row)) return "row-manual";
  return "row-unmatched";
}

function getStatusBadgeClass(row) {
  if (isMatched(row)) return "status-badge status-matched";
  if (needsManualReview(row)) return "status-badge status-manual";
  return "status-badge status-unmatched";
}
</script>

<style scoped>
.results-panel {
  background: white;
  border: 1px solid #d9dde3;
  border-radius: 8px;
  overflow: hidden;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #e4e7ec;
}

.results-header h3 {
  margin: 0;
  font-size: 15px;
}

.results-header span {
  color: #667085;
  font-size: 13px;
}

.table-scroll {
  overflow: auto;
}

.results-table {
  width: 100%;
  min-width: 1120px;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 8px 10px;
  border-bottom: 1px solid #eef1f5;
  text-align: left;
  vertical-align: middle;
}

th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  color: #475467;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

tbody tr:not(.details-row) {
  cursor: pointer;
}

tbody tr:not(.details-row):hover {
  background: #f8fafc;
}

.row-matched {
  box-shadow: inset 3px 0 0 #16a34a;
}

.row-unmatched {
  box-shadow: inset 3px 0 0 #dc2626;
}

.row-manual {
  box-shadow: inset 3px 0 0 #d97706;
}

.number-cell {
  text-align: right;
  white-space: nowrap;
}

.image-cell {
  width: 58px;
}

.thumb {
  width: 42px;
  height: 42px;
  display: block;
  object-fit: cover;
  border: 1px solid #e4e7ec;
  border-radius: 6px;
  background: #f8fafc;
}

.matched-model {
  min-width: 220px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-matched {
  background: #dcfce7;
  color: #166534;
}

.status-unmatched {
  background: #fee2e2;
  color: #991b1b;
}

.status-manual {
  background: #fef3c7;
  color: #92400e;
}

.details-row td {
  padding: 0;
  background: #fbfcfe;
}

.details-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 14px;
  padding: 14px;
}

.details-main h4 {
  margin: 0 0 12px;
  font-size: 14px;
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 14px;
  margin: 0;
}

dl div {
  min-width: 0;
}

dt {
  margin-bottom: 3px;
  color: #667085;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

dd {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

.debug-box {
  min-width: 0;
  border: 1px solid #e4e7ec;
  border-radius: 6px;
  background: white;
}

.debug-box summary {
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 700;
}

pre {
  max-height: 340px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  border-top: 1px solid #e4e7ec;
  font-size: 12px;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .details-grid {
    grid-template-columns: 1fr;
  }

  dl {
    grid-template-columns: 1fr;
  }
}
</style>
