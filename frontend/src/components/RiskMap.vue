
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// 从父页面接收FastAPI返回的问题列表

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },

  // 后端预算方案中选中的项目编号
  selectedIds: {
    type: Array,
    default: () => []
  },

  // 是否已经生成过预算方案
  hasPlan: {
    type: Boolean,
    default: false
  }
})

// 转换为字符串集合，方便匹配P001等编号
const selectedSet = computed(
  () => new Set(props.selectedIds.map(String))
)

const selectedPointCount = computed(
  () => points.value.filter(
    item => selectedSet.value.has(String(item.id))
  ).length
)

const mapHost = ref(null)
const selected = ref(null)

let map = null
let pointLayer = null

const colors = {
  '高': '#cf6c55',
  '中': '#d5a34e',
  '低': '#27977c'
}

// 只保留有有效经纬度的记录
const points = computed(() =>
  props.items.filter(item => {
    const lat = Number(item.lat)
    const lon = Number(item.lon)

    return Number.isFinite(lat) &&
      Number.isFinite(lon) &&
      lat >= -90 && lat <= 90 &&
      lon >= -180 && lon <= 180 &&
      item.lat !== '' &&
      item.lon !== ''
  })
)

// 根据传入的数据绘制风险点

function drawPoints(fitView = true) {
  if (!map || !pointLayer) return

  pointLayer.clearLayers()

  const bounds = []
  const highlightedMarkers = []

  points.value.forEach(item => {
    const coordinate = [
      Number(item.lat),
      Number(item.lon)
    ]

    const riskColor =
      colors[item.risk_level] || '#27977c'

    // 判断当前项目是否被预算方案选中
    const isSelected =
      props.hasPlan &&
      selectedSet.value.has(String(item.id))

    const marker = L.circleMarker(coordinate, {
      radius: isSelected ? 13 : 9,

      // 选中项目使用深青色外环
      color: isSelected ? '#173f46' : '#ffffff',

      weight: isSelected ? 4 : 2,

      fillColor: riskColor,

      // 生成方案后，弱化未选中的点
      fillOpacity:
        !props.hasPlan || isSelected ? 0.95 : 0.28,

      opacity:
        !props.hasPlan || isSelected ? 1 : 0.55
    })

    const tooltip = document.createElement('span')
    tooltip.textContent = String(item.name || '未命名点位')

    marker.bindTooltip(tooltip)

    marker.on('click', () => {
      selected.value = item
    })

    marker.addTo(pointLayer)

    if (isSelected) {
      highlightedMarkers.push(marker)
    }

    bounds.push(coordinate)
  })

  // 让选中的项目显示在其他点位上方
  highlightedMarkers.forEach(marker => {
    marker.bringToFront()
  })

  // 尽量保留用户正在查看的点位
  selected.value =
    points.value.find(
      item => String(item.id) === String(selected.value?.id)
    ) || points.value[0] || null

  // 只有数据位置变化时才重新定位地图
  if (fitView) {
    if (bounds.length > 1) {
      map.fitBounds(bounds, {
        padding: [35, 35],
        maxZoom: 16
      })
    } else if (bounds.length === 1) {
      map.setView(bounds[0], 16)
    }
  }
}

onMounted(() => {
  map = L.map(mapHost.value, {
    zoomControl: true
  })

  // OpenStreetMap底图
  
const baseLayer = L.tileLayer(
  'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">' +
      'OpenStreetMap</a> contributors',
    maxZoom: 19
  }
)

// 记录地图底图加载失败的具体地址
baseLayer.on('tileerror', (event) => {
  console.warn(
    '地图底图加载失败：',
    event.tile?.src
  )
})

baseLayer.addTo(map)

  map.setView([35, 105], 4)

  L.control.scale({
    imperial: false
  }).addTo(map)

  pointLayer = L.layerGroup().addTo(map)

  drawPoints()
})


// 风险数据变化时重新绘制并调整地图范围
watch(
  () => props.items,
  () => drawPoints(true),
  { deep: true }
)

// 预算选中项目变化时只更新点位样式
watch(
  () => props.selectedIds,
  () => drawPoints(false),
  { deep: true }
)

// 首次生成方案时更新显示状态
watch(
  () => props.hasPlan,
  () => drawPoints(false)
)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <section class="risk-map-panel">

    <header class="map-header">
      <div>
        <h2>社区空间风险地图</h2>
        <p>点击风险点，查看问题诊断与改造建议</p>
      </div>

      <span class="point-count">
        {{ points.length }} 个点位
      </span>
    </header>

    <div class="map-wrap">
      <div ref="mapHost" class="map-canvas"></div>
    </div>

    <div class="map-legend">
      <span><i class="legend-dot high"></i>高风险</span>
      <span><i class="legend-dot medium"></i>中风险</span>
      <span><i class="legend-dot low"></i>低风险</span>
    </div>

    <div v-if="selected" class="point-details">
      <div class="details-top">
        <strong>{{ selected.name }}</strong>

        <span class="risk-label">
          {{ selected.risk_level }}风险
        </span>
      </div>
      
<div v-if="props.hasPlan" class="selection-status">
  <span
    v-if="selectedSet.has(String(selected.id))"
    class="selected-badge"
  >
    ✓ 已纳入本轮预算方案
  </span>

  <span v-else class="unselected-badge">
    本轮暂未选中
  </span>
</div>

      <p>问题类型：{{ selected.issue_type }}</p>
      <p>
        模型风险分：
        {{ Number(selected.risk_score).toFixed(1) }}
      </p>

      <p>
        核验状态：
        {{ selected.verified ? '已核验' : '尚未核验' }}
      </p>

      <div class="suggestion">
        <b>改造建议</b>
        <p>{{ selected.suggestion }}</p>
      </div>
    </div>

    <div v-else class="empty-state">
      当前没有有效的风险点坐标。
    </div>

    <p class="map-disclaimer">
      当前使用演示数据时，风险点位置不代表真实社区调查结果。
    </p>
  </section>
</template>




<style scoped>
.risk-map-panel {
  background: #ffffff;
  border: 1px solid #e1ebe7;
  border-radius: 16px;
  padding: 22px;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 15px;
  margin-bottom: 18px;
}

.map-header h2 {
  margin: 0;
  font-size: 19px;
  color: #204850;
}

.map-header p {
  margin: 8px 0 0;
  font-size: 12px;
  color: #879b9d;
}

.point-count {
  background: #e8f5ef;
  color: #258b70;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 12px;
  white-space: nowrap;
}

.map-wrap {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e2eae6;
}

.map-canvas {
  height: 390px;
  width: 100%;
  z-index: 0;
}

.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 15px 2px;
  font-size: 12px;
  color: #6e8888;
}

.map-legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.high {
  background: #cf6c55;
}

.medium {
  background: #d5a34e;
}

.low {
  background: #27977c;
}

.point-details {
  background: #f5f9f7;
  border-radius: 12px;
  padding: 18px;
}

.details-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.details-top strong {
  color: #234d53;
  font-size: 16px;
}

.risk-label {
  background: #fceee8;
  color: #c46c52;
  border-radius: 7px;
  padding: 5px 9px;
  font-size: 12px;
}

.point-details > p {
  font-size: 13px;
  color: #617d7f;
  margin: 12px 0;
}

.suggestion {
  border-left: 3px solid #26967d;
  padding: 9px 13px;
  background: #ebf5f1;
  border-radius: 0 8px 8px 0;
}

.suggestion b {
  font-size: 13px;
  color: #268a72;
}

.suggestion p {
  font-size: 12px;
  line-height: 1.7;
  color: #52736f;
  margin-bottom: 0;
}

.empty-state {
  color: #849798;
  padding: 22px;
  text-align: center;
  font-size: 13px;
}

.map-disclaimer {
  font-size: 11px;
  color: #91a3a3;
  line-height: 1.6;
  margin: 16px 0 0;
}

@media (max-width: 700px) {
  .risk-map-panel {
    padding: 14px;
  }

  .map-canvas {
    height: 310px;
  }

  .map-header {
    flex-direction: column;
  }
}


.selection-status {
  margin: 12px 0;
}

.selected-badge,
.unselected-badge {
  display: inline-block;
  padding: 7px 11px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
}

.selected-badge {
  background: #e0f3e9;
  color: #18785d;
}

.unselected-badge {
  background: #edf1ef;
  color: #7e908c;
}
</style>