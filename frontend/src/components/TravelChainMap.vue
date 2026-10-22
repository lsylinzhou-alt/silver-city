
<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'

// 后端API地址
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'

// 从父页面接收当前预算选中的改造项目
const props = defineProps({
  selectedIds: {
    type: Array,
    default: () => []
  }
})

// 页面状态
const profile = ref('轮椅')
const viewMode = ref('after')
const selectedRouteKey = ref('')
const data = ref(null)
const loading = ref(false)
const error = ref('')

let requestVersion = 0

// 获取出行链数据
async function loadChains() {
  const version = ++requestVersion
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(
      API_BASE + '/api/travel-chains',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          selected_ids: props.selectedIds.map(String),
          profile: profile.value,
          verified_only: false
        })
      }
    )

    if (!response.ok) {
      throw new Error(
        `出行链接口返回HTTP ${response.status}`
      )
    }

    const result = await response.json()

    if (
      !Array.isArray(result.nodes) ||
      !Array.isArray(result.edges) ||
      !Array.isArray(result.routes)
    ) {
      throw new Error('接口返回的数据结构不完整')
    }

    // 忽略已经过期的请求
    if (version !== requestVersion) return

    data.value = result

    // 优先展示一条因改造而新打通的出行链
    const preferred =
      result.routes.find(r => r.newly_connected) ||
      result.routes[0]

    selectedRouteKey.value = preferred
      ? routeKey(preferred)
      : ''

  } catch (err) {
    if (version === requestVersion) {
      error.value = err.message
      data.value = null
    }
  } finally {
    if (version === requestVersion) {
      loading.value = false
    }
  }
}

function routeKey(route) {
  return `${route.origin_id}::${route.destination_id}`
}

// 监听方案项目及通行能力变化
watch(
  [
    () => props.selectedIds.map(String).join('|'),
    profile
  ],
  loadChains,
  { immediate: true }
)

onBeforeUnmount(() => {
  requestVersion++
})

// 取得路线
const routes = computed(
  () => data.value?.routes || []
)

const currentRoute = computed(() =>
  routes.value.find(
    r => routeKey(r) === selectedRouteKey.value
  ) || routes.value[0] || null
)

const isAfter = computed(
  () => viewMode.value === 'after'
)

const reachable = computed(() => {
  if (!currentRoute.value) return false
  return isAfter.value
    ? currentRoute.value.after_reachable
    : currentRoute.value.before_reachable
})

// ============================
// 地理坐标转换成SVG平面位置
// ============================

const positions = computed(() => {
  const nodes = (data.value?.nodes || [])
    .map(n => ({
      ...n,
      id: String(n.id),
      lat: Number(n.lat),
      lon: Number(n.lon)
    }))
    .filter(n =>
      Number.isFinite(n.lat) &&
      Number.isFinite(n.lon)
    )

  if (!nodes.length) return []

  const centerLat =
    nodes.reduce((s, n) => s + n.lat, 0) /
    nodes.length

  const centerLon =
    nodes.reduce((s, n) => s + n.lon, 0) /
    nodes.length

  const cosLat = Math.cos(
    centerLat * Math.PI / 180
  )

  // 局部坐标投影，仅用于小区域示意
  const projected = nodes.map(n => ({
    ...n,
    px: (n.lon - centerLon) * cosLat * 111320,
    py: (n.lat - centerLat) * 111320
  }))

  const xs = projected.map(n => n.px)
  const ys = projected.map(n => n.py)

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const scale = Math.min(
    740 / Math.max(maxX - minX, 20),
    380 / Math.max(maxY - minY, 20)
  )

  const midX = (minX + maxX) / 2
  const midY = (minY + maxY) / 2

  return projected.map(n => ({
    ...n,
    x: 450 + (n.px - midX) * scale,
    y: 260 - (n.py - midY) * scale
  }))
})

const positionIndex = computed(() =>
  Object.fromEntries(
    positions.value.map(n => [n.id, n])
  )
)

// 生成道路连线
const networkEdges = computed(() =>
  (data.value?.edges || [])
    .map((edge, index) => ({
      ...edge,
      key: index,
      a: positionIndex.value[String(edge.start)],
      b: positionIndex.value[String(edge.end)]
    }))
    .filter(edge => edge.a && edge.b)
)

function isBlocked(edge) {
  return isAfter.value
    ? edge.blocked_after
    : edge.blocked_before
}

// 当前选中出行链的路径
const routeSegments = computed(() => {
  if (!currentRoute.value || !reachable.value) {
    return []
  }

  const path = isAfter.value
    ? currentRoute.value.after_path
    : currentRoute.value.before_path

  if (!Array.isArray(path)) return []

  const lines = []

  for (let i = 0; i < path.length - 1; i++) {
    const a = positionIndex.value[String(path[i])]
    const b = positionIndex.value[String(path[i + 1])]

    if (a && b) {
      lines.push({ a, b, key: i })
    }
  }

  return lines
})

function isHome(node) {
  return node.kind === '住宅'
}

function isService(node) {
  return [
    '公交站', '卫生站', '菜市场',
    '便利店', '公共服务'
  ].includes(node.kind)
}

function isFocusNode(node) {
  if (!currentRoute.value) return false

  return (
    node.id === String(currentRoute.value.origin_id) ||
    node.id === String(currentRoute.value.destination_id)
  )
}

const currentDistance = computed(() => {
  if (!currentRoute.value || !reachable.value) {
    return null
  }

  return isAfter.value
    ? currentRoute.value.after_distance_m
    : currentRoute.value.before_distance_m
})
</script>

<template>
  <section class="travel-panel">

    <div class="travel-heading">
      <div>
        <span class="eyebrow">MOBILITY NETWORK ANALYSIS</span>
        <h2>生活出行链 · 空间推演</h2>
        <p>对比社区改造前后，完整生活路线的可通行情况</p>
      </div>

      <span class="simulation-tag">
        模拟路网
      </span>
    </div>

    <!-- 参数与地图状态切换 -->
    <div class="travel-toolbar">
      <label class="travel-select">
        <span>通行能力档案</span>
        <select v-model="profile">
          <option>一般步行</option>
          <option>助行器</option>
          <option>轮椅</option>
        </select>
      </label>

      <div class="stage-switch">
        <button
          type="button"
          :class="{ active: viewMode === 'before' }"
          @click="viewMode = 'before'"
        >
          改造前
        </button>

        <button
          type="button"
          :class="{ active: viewMode === 'after' }"
          @click="viewMode = 'after'"
        >
          方案实施后
        </button>
      </div>
    </div>

    <div v-if="loading" class="travel-message">
      正在计算生活出行链……
    </div>

    <div v-else-if="error" class="travel-error">
      {{ error }}
      <button type="button" @click="loadChains">
        重新计算
      </button>
    </div>

    <template v-else-if="data">
      <!-- 出行链指标 -->
      <div class="travel-stats">
        <div>
          <small>改造前可通行</small>
          <strong>
            {{ data.summary.before_reachable }}
            / {{ data.summary.total_pairs }}
          </strong>
        </div>

        <div>
          <small>方案后可通行</small>
          <strong>
            {{ data.summary.after_reachable }}
            / {{ data.summary.total_pairs }}
          </strong>
        </div>

        <div>
          <small>新增可通行链路</small>
          <strong class="green">
            +{{ data.summary.newly_connected }}
          </strong>
        </div>
      </div>

      <!-- SVG路网 -->
      <div class="network-stage">
        <svg
          v-if="positions.length"
          viewBox="0 0 900 520"
          class="network-svg"
          role="img"
          aria-label="社区生活出行链路网推演示意图"
        >
          <rect
            x="0" y="0"
            width="900" height="520"
            fill="#edf4ef"
          />

          <!-- 淡色背景网格 -->
          <g stroke="#dbe7df" stroke-width="1">
            <line
              v-for="n in 8"
              :key="'v' + n"
              :x1="n * 100"
              y1="0"
              :x2="n * 100"
              y2="520"
            />

            <line
              v-for="n in 5"
              :key="'h' + n"
              x1="0"
              :y1="n * 90"
              x2="900"
              :y2="n * 90"
            />
          </g>

          <!-- 全部道路 -->
          <g v-for="edge in networkEdges" :key="edge.key">
            <line
              :x1="edge.a.x"
              :y1="edge.a.y"
              :x2="edge.b.x"
              :y2="edge.b.y"
              :stroke="isBlocked(edge) ? '#D78970' : '#8CAF9F'"
              :stroke-width="isBlocked(edge) ? 5 : 6"
              :stroke-dasharray="isBlocked(edge) ? '10 7' : undefined"
              stroke-linecap="round"
            >
              <title>
                {{ edge.start }} → {{ edge.end }}
                {{ isBlocked(edge) ? '当前受阻' : '模型可通行' }}
              </title>
            </line>
          </g>

          <!-- 选中的完整出行路线 -->
          <g>
            <line
              v-for="segment in routeSegments"
              :key="segment.key"
              :x1="segment.a.x"
              :y1="segment.a.y"
              :x2="segment.b.x"
              :y2="segment.b.y"
              stroke="#139C80"
              stroke-width="10"
              stroke-linecap="round"
            />
          </g>

          <!-- 路网节点 -->
          <g v-for="node in positions" :key="node.id">
            <circle
              :cx="node.x"
              :cy="node.y"
              :r="isHome(node) ? 11 : isService(node) ? 10 : 5"
              :fill="isHome(node)
                ? '#214A52'
                : isService(node)
                  ? '#DDA45D'
                  : '#8BB3A6'"
              :stroke="isFocusNode(node) ? '#14987D' : '#FFFFFF'"
              :stroke-width="isFocusNode(node) ? 4 : 2"
            >
              <title>{{ node.name }}</title>
            </circle>

            <text
              v-if="isHome(node) || isService(node)"
              :x="node.x + (node.x > 560 ? -14 : 14)"
              :y="node.y - 13"
              :text-anchor="node.x > 560 ? 'end' : 'start'"
              class="node-name"
            >
              {{ node.name }}
            </text>
          </g>
        </svg>

        <div v-else class="travel-message">
          当前没有可以绘制的路网节点。
        </div>
      </div>

      <div class="network-legend">
        <span><i class="line-green"></i> 模型可通行道路</span>
        <span><i class="line-orange"></i> 当前受阻道路</span>
        <span><i class="line-selected"></i> 当前选择的路线</span>
      </div>

      <!-- 指定一条出行链查看 -->
      <div class="route-details">
        <label>
          查看住宅到生活服务设施的出行链

          <select v-model="selectedRouteKey">
            <option
              v-for="route in routes"
              :key="routeKey(route)"
              :value="routeKey(route)"
            >
              {{ route.origin }} → {{ route.destination }}
            </option>
          </select>
        </label>

        <template v-if="currentRoute">
          <div
            class="route-status"
            :class="{ unavailable: !reachable }"
          >
            <strong>
              {{ reachable ? '✓ 模型可通行' : '！当前模型不可通行' }}
            </strong>

            <span v-if="currentDistance !== null">
              估计路径长度：
              {{ Number(currentDistance).toFixed(0) }} 米
            </span>

            <span v-else>
              当前条件下未找到符合规则的路线
            </span>
          </div>

          <p
            v-if="currentRoute.newly_connected"
            class="new-route-tip"
          >
            这条生活出行链在当前方案实施后由不可通行变为模型可通行。
          </p>
        </template>
      </div>

      <p class="network-note">
        当前为模拟空间拓扑示意，线段仅表示已录入节点之间的连接关系。
        不是真实街道走向或安全导航路线。道路通行结论仍需实地核验。
      </p>
    </template>
  </section>
</template>

<style scoped>
.travel-panel {
  background: #fff;
  border: 1px solid #e0eae5;
  border-radius: 16px;
  padding: 23px;
  color: #244b51;
}

.travel-heading {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  align-items: flex-start;
  margin-bottom: 22px;
}

.eyebrow {
  color: #1c987c;
  font-size: 10px;
  letter-spacing: 2px;
  font-weight: 700;
}

.travel-heading h2 {
  font-size: 21px;
  margin: 10px 0;
}

.travel-heading p {
  font-size: 12px;
  color: #829899;
  margin: 0;
}

.simulation-tag {
  background: #fff4e6;
  color: #a4763b;
  padding: 8px 11px;
  font-size: 11px;
  border-radius: 7px;
  white-space: nowrap;
}

.travel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: end;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 20px;
}

.travel-select,
.route-details label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: #718a88;
}

.travel-panel select {
  background: #f5f8f6;
  color: #244b51;
  border: 1px solid #dde7e2;
  padding: 10px 12px;
  border-radius: 9px;
  min-width: 160px;
  font-size: 13px;
}

.stage-switch {
  display: flex;
  gap: 5px;
  padding: 4px;
  border-radius: 10px;
  background: #edf2ef;
}

.stage-switch button {
  padding: 10px 15px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #748c88;
  cursor: pointer;
}

.stage-switch button.active {
  background: #fff;
  color: #198c73;
  font-weight: 700;
  box-shadow: 0 2px 8px #173f4610;
}

.travel-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 17px;
}

.travel-stats > div {
  background: #f4f8f6;
  border-radius: 10px;
  padding: 15px;
}

.travel-stats small {
  display: block;
  color: #839996;
  font-size: 11px;
  margin-bottom: 9px;
}

.travel-stats strong {
  font-size: 24px;
  color: #244b51;
}

.travel-stats strong.green {
  color: #179477;
}

.network-stage {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e0ebe4;
  background: #edf4ef;
}

.network-svg {
  display: block;
  width: 100%;
  height: auto;
}

.node-name {
  fill: #315b60;
  font-size: 17px;
  font-weight: 650;
  paint-order: stroke;
  stroke: #edf4ef;
  stroke-width: 5px;
  stroke-linejoin: round;
}

.network-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 17px;
  margin: 16px 0;
  font-size: 11px;
  color: #768e8b;
}

.network-legend span {
  display: flex;
  align-items: center;
  gap: 7px;
}

.network-legend i {
  display: inline-block;
  width: 22px;
  height: 0;
  border-top: 4px solid;
}

.line-green { border-color: #8CAF9F !important; }
.line-orange {
  border-color: #D78970 !important;
  border-top-style: dashed !important;
}
.line-selected { border-color: #139C80 !important; }

.route-details {
  background: #f5f9f7;
  padding: 17px;
  border-radius: 11px;
}

.route-details select {
  width: 100%;
}

.route-status {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
  font-size: 12px;
  color: #198e73;
}

.route-status.unavailable {
  color: #b87556;
}

.new-route-tip {
  margin: 14px 0 0;
  font-size: 12px;
  color: #198e73;
  line-height: 1.6;
}

.network-note {
  color: #91a3a0;
  font-size: 11px;
  line-height: 1.7;
  margin-top: 17px;
}

.travel-message,
.travel-error {
  padding: 45px 15px;
  text-align: center;
  border-radius: 10px;
  background: #f5f8f6;
  font-size: 13px;
}

.travel-error {
  color: #b95f4c;
}

.travel-error button {
  margin-left: 12px;
  cursor: pointer;
}

@media (max-width: 700px) {
  .travel-panel { padding: 14px; }
  .travel-heading { flex-direction: column; }
  .travel-stats { gap: 7px; }
  .travel-stats > div { padding: 10px; }
  .travel-stats strong { font-size: 19px; }
  .stage-switch { width: 100%; }
  .stage-switch button { flex: 1; }
}
</style>