
<script setup>
import { ref, computed, onMounted } from 'vue'
import RiskMap from './components/RiskMap.vue'
import TravelChainMap from './components/TravelChainMap.vue'

// FastAPI后端地址

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'
).replace(/\/+$/, '')

// 页面数据
const dashboard = ref(null)
const problems = ref([])
const budget = ref(5)

const mode = ref('basic')
const guaranteeInfo = ref(null)

// 用于避免旧请求结果覆盖新预算结果
let requestVersion = 0
const plan = ref(null)

const loading = ref(false)
const dashboardError = ref('')
const planError = ref('')

// 计算属性
const selectedProjects = computed(
  () => plan.value?.selected || []
)

const spendingPercent = computed(() => {
  if (!plan.value || budget.value <= 0) return 0
  return Math.min(
    100,
    (plan.value.spent_wan / budget.value) * 100
  )
})

function money(value) {
  return Number(value || 0).toFixed(2)
}

// 统一发送HTTP请求
async function requestAPI(path, options = {}) {
  let response

  try {
    response = await fetch(API_BASE + path, options)
  } catch {
    throw new Error(
      '无法连接FastAPI，请检查8000端口是否运行'
    )
  }

  if (!response.ok) {
    throw new Error(
      `后端请求失败：HTTP ${response.status}`
    )
  }

  return await response.json()
}

// 获取首页数据
async function loadDashboard() {
  dashboardError.value = ''

  try {
    const [stats, issueData] = await Promise.all([
      requestAPI('/api/dashboard'),
      requestAPI('/api/problems')
    ])

    dashboard.value = stats
    problems.value = issueData.items || []
  } catch (error) {
    dashboardError.value = error.message
  }
}

// 调用预算优化算法

// 参数变化后，清除旧方案，避免展示过期结果
function invalidatePlan() {
  requestVersion += 1
  plan.value = null
  guaranteeInfo.value = null
  planError.value = ''
  loading.value = false
}

// 根据用户选择，调用不同的后端算法
async function generatePlan() {
  const version = ++requestVersion

  const currentMode = mode.value
  const currentBudget = Number(budget.value)

  loading.value = true
  planError.value = ''
  plan.value = null
  guaranteeInfo.value = null

  try {
    const apiPath = currentMode === 'fair'
      ? '/api/guarantee-plan'
      : '/api/plan'

    const result = await requestAPI(apiPath, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        budget_wan: currentBudget
      })
    })

    // 用户已切换预算或模式时，丢弃旧请求
    if (version !== requestVersion) return

    if (currentMode === 'fair') {
      guaranteeInfo.value = result

      if (result.status === '预算内可行') {
        // 统一两种接口的支出字段
        plan.value = {
          ...result,
          spent_wan: Number(result.cost_wan)
        }
      } else {
        // 保障不可行时，不展示超预算项目
        plan.value = null
      }
    } else {
      plan.value = result
    }

  } catch (error) {
    if (version === requestVersion) {
      planError.value = error.message
      plan.value = null
    }
  } finally {
    if (version === requestVersion) {
      loading.value = false
    }
  }
}

// 页面打开后自动获取数据
onMounted(() => {
  loadDashboard()
  generatePlan()
})
</script>

<template>
  <div class="shell">

    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">✦</div>
        <div>
          <strong>银龄智城</strong>
          <small>SILVER CITY</small>
        </div>
      </div>

      <p class="nav-label">智慧社区工作台</p>

      <nav class="navigation">
        <a href="#overview" class="nav-item active">
          ◈　治理总览
        </a>
        <a href="#risks" class="nav-item">
          ◉　社区风险诊断
        </a>
        
          <a href="#mobility" class="nav-item">
          ↗　生活出行链推演
        </a>  
        <a href="#planning" class="nav-item">
          ▣　微更新智能决策
        </a>
      </nav>

      <div class="sidebar-bottom">
        <div class="side-notice">
          <span class="dot"></span>
          竞赛原型运行中
          <p>让有限预算改善更多生活出行</p>
        </div>
        <small>© 2026 银龄智城</small>
      </div>
    </aside>

    <!-- 主要内容 -->
    <main class="main">

      <header class="topbar">
        <div class="breadcrumb">
          社区更新管理 / <b>智能决策驾驶舱</b>
        </div>

        <span
          class="connection"
          :class="{ offline: !dashboard }"
        >
          ● {{ dashboard ? '后端已连接' : '等待后端连接' }}
        </span>
      </header>

      <div class="content">

        <!-- 页面标题 -->
        <section id="overview" class="hero">
          <div class="eyebrow">
            SPATIAL DECISION INTELLIGENCE
          </div>

          <h1>
            让每一笔更新预算，真正打通一条生活之路。
          </h1>

          <p>
            社区适老化数字体检 · 空间风险诊断 ·
            微更新智能决策
          </p>
        </section>

        <div class="notice">
          <b>演示模式</b>
          当前数据包含模拟社区问题、成本和风险评分，
          不代表真实工程评估结果。
        </div>

        <!-- 错误提醒 -->
        <div
          v-if="dashboardError"
          class="error-box"
        >
          {{ dashboardError }}
          <button @click="loadDashboard">
            重新连接
          </button>
        </div>

        <!-- 四张统计卡片 -->
        <section class="stats-grid">

          <div class="stat-card">
            <span>已登记空间问题</span>
            <strong>
              {{ dashboard?.problem_count ?? '—' }}
            </strong>
            <small>社区问题总数</small>
          </div>

          <div class="stat-card">
            <span>高风险问题</span>
            <strong>
              {{ dashboard?.high_risk_count ?? '—' }}
            </strong>
            <small>需要重点关注</small>
          </div>

          <div class="stat-card">
            <span>已人工核验</span>
            <strong>
              {{ dashboard?.verified_count ?? '—' }}
            </strong>
            <small>具备核验记录的点位</small>
          </div>

          <div class="stat-card">
            <span>候选改造总成本</span>
            <strong>
              {{
                dashboard
                  ? money(dashboard.estimated_total_cost_wan)
                  : '—'
              }}
            </strong>
            <small>单位：万元</small>
          </div>

        </section>

        <div class="main-grid">
          
<!-- 左侧：核心生活出行链推演 -->
<section
  id="mobility"
  class="mobility-section mobility-primary"
>
  <TravelChainMap
    v-if="plan"
    :selected-ids="selectedProjects.map(item => String(item.id))"
  />

  <div v-else class="mobility-empty">
    <h2>生活出行链 · 空间推演</h2>

    <p v-if="loading">
      正在计算改造方案……
    </p>

    <p
      v-else-if="
        mode === 'fair' &&
        guaranteeInfo?.status === '预算不足'
      "
    >
      当前预算不足以满足最低保障要求。
      请增加预算后重新生成方案。
    </p>

    <p v-else>
      请先在右侧选择优化目标、设置预算，
      点击“生成智能改造方案”。
      系统将展示完整生活出行链的改造前后变化。
    </p>
  </div>
</section>

          <!-- 右侧：智能预算优化 -->
          <section id="planning" class="panel planning">

            <div class="panel-heading">
              <div>
                <h2>智能微更新决策</h2>
                <p>有限预算下的候选项目优化</p>
              </div>
              <span class="pill green">智能计算</span>
            </div>

            <div class="budget-area">
              
<div class="mode-picker">
  <strong>请选择改造决策目标</strong>

  <label class="mode-option">
    <input
      type="radio"
      value="basic"
      v-model="mode"
      @change="invalidatePlan"
    />
    <span>
      <b>综合收益优先</b>
      <small>优先提高模型代理收益分</small>
    </span>
  </label>

  <label class="mode-option">
    <input
      type="radio"
      value="fair"
      v-model="mode"
      @change="invalidatePlan"
    />
    <span>
      <b>公平保障优先</b>
      <small>优先保障最弱楼栋的基本服务可达性</small>
    </span>
  </label>
</div>
              <div class="budget-title">
                <label for="budget">本轮改造预算</label>
                <strong>
                  {{ Number(budget).toFixed(1) }}
                  <small>万元</small>
                </strong>
              </div>
            

              
<input
  id="budget"
  type="range"
  min="0"
  max="15"
  step="0.5"
  v-model.number="budget"
  @input="invalidatePlan"
/>

              <div class="range-labels">
                <span>0万</span>
                <span>7.5万</span>
                <span>15万</span>
              </div>

              <button
                class="action-button"
                :disabled="loading"
                @click="generatePlan"
              >
                {{
                  loading
                    ? '正在计算方案……'
                    : '生成智能改造方案 →'
                }}
              </button>
            </div>

            <div v-if="planError" class="error-box">
              {{ planError }}
            </div>

            
<!-- 公平保障方案结果 -->
<div
  v-if="mode === 'fair' && guaranteeInfo"
  class="fairness-result"
>
  <template v-if="guaranteeInfo.status === '预算内可行'">
    <strong class="result-success">
      ✓ 当前预算满足最低保障要求
    </strong>

    <p>
      最低保障预算：
      {{ money(guaranteeInfo.minimum_cost_wan) }} 万元
    </p>

    <p>
      本次分层优化实际支出：
      {{ money(guaranteeInfo.cost_wan) }} 万元
    </p>

    <p>
      最弱楼栋可通行率：
      {{ Number(guaranteeInfo.worst_home_pct).toFixed(1) }}%
    </p>

    <p>
      三群体平均可通行率：
      {{ Number(guaranteeInfo.mean_coverage_pct).toFixed(1) }}%
    </p>
  </template>

  <template v-else-if="guaranteeInfo.status === '预算不足'">
    <strong class="result-warning">
      当前预算不足，无法满足最低保障条件
    </strong>

    <p>
      最低保障需要：
      {{ money(guaranteeInfo.minimum_cost_wan) }} 万元
    </p>

    <p>
      尚需增加预算：
      {{ money(guaranteeInfo.budget_gap_wan) }} 万元
    </p>

    <p>
      当前不生成满足保障要求的可执行项目组合。
    </p>
  </template>

  <template v-else>
    <strong class="result-warning">
      当前候选项目无法满足保障目标
    </strong>
    <p>
      {{ guaranteeInfo.reason || '请检查路网连接与候选改造项目。' }}
    </p>
  </template>
</div>

            <template v-if="plan">

              <div class="result-bar">
                <div>
                  <small>推荐使用预算</small>
                  <strong>
                    ¥ {{ money(plan.spent_wan) }} 万
                  </strong>
                </div>
                <div>
                  <small>模型收益分</small>
                  <strong>
                    {{ money(plan.benefit_score) }}
                  </strong>
                </div>
              </div>

              <div class="progress-track">
                <div
                  class="progress-fill"
                  :style="{ width: spendingPercent + '%' }"
                ></div>
              </div>

              <div class="plan-heading">
                推荐优先改造项目
                <span>{{ selectedProjects.length }} 项</span>
              </div>

              <div
                v-for="(item, index) in selectedProjects"
                :key="item.id"
                class="project-item"
              >
                <div class="project-number">
                  {{ index + 1 }}
                </div>

                <div class="project-content">
                  <strong>{{ item.name }}</strong>
                  <p>{{ item.suggestion }}</p>
                </div>

                <b class="project-price">
                  {{ money(item.cost_wan) }} 万
                </b>
              </div>

              <div
                v-if="selectedProjects.length === 0"
                class="empty"
              >
                当前预算内没有选中的改造项目。
              </div>

              
<p class="panel-footnote">
  {{
    mode === 'fair'
      ? '当前采用基本可达性保障约束与分层公平优化，优先改善最弱楼栋的服务可达性。'
      : '当前采用基础代理收益最大化优化，不强制保证所有楼栋达到最低服务覆盖要求。'
  }}
  所有计算均基于模拟数据，并非真实工程评估结论。
</p>

            </template>
          </section>
        </div>
        
<!-- ===================================== -->
<!-- 生活出行链与空间推演 -->
<!-- ===================================== -->



        
<!-- 下方：社区风险诊断地图 -->
<section id="risks" class="risk-section">
  <RiskMap
    :items="problems"
    :selected-ids="selectedProjects.map(item => String(item.id))"
    :has-plan="plan !== null"
  />
</section>
        <footer class="footer">
          <span>
            银龄智城 · 社区适老化空间决策平台
          </span>
          <span>
            Vue 3 前端 · FastAPI 后端
          </span>
        </footer>

      </div>
    </main>
  </div>
</template>

<style>
/* 全局重置：覆盖Vite默认欢迎页样式 */
:root {
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
  color: #193f46;
  background: #f5f7f6;
}

* {
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  min-width: 320px;
  min-height: 100vh;
  margin: 0 !important;
  padding: 0 !important;
  max-width: none !important;
}

body {
  display: block !important;
  background: #f5f7f6;
}

#app {
  text-align: left !important;
}

.shell {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #173d44;
  color: white;
  padding: 30px 18px;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 52px;
}

.brand-icon {
  background: #23977d;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 25px;
}

.brand strong {
  display: block;
  font-size: 21px;
}

.brand small {
  display: block;
  margin-top: 4px;
  font-size: 10px;
  letter-spacing: 2px;
  color: #9ec9c0;
}

.nav-label {
  color: #8cb2ae;
  font-size: 11px;
  padding-left: 13px;
  margin-bottom: 14px;
}

.navigation {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.nav-item {
  color: #c4d9d6;
  padding: 14px 13px;
  border-radius: 9px;
  text-decoration: none;
  font-size: 14px;
}

.nav-item:hover,
.nav-item.active {
  background: #29535a;
  color: white;
}

.sidebar-bottom {
  margin-top: auto;
  padding-top: 30px;
}

.side-notice {
  border: 1px solid #476870;
  padding: 15px;
  border-radius: 11px;
  font-size: 13px;
}

.side-notice p {
  color: #a9c6c2;
  font-size: 11px;
  line-height: 1.6;
}

.dot {
  color: #73dab0;
}

.sidebar-bottom > small {
  display: block;
  margin-top: 22px;
  color: #8eaeac;
}

.main {
  flex: 1;
  min-width: 0;
}

.topbar {
  height: 72px;
  background: white;
  border-bottom: 1px solid #e2ebe7;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 35px;
}

.breadcrumb {
  font-size: 13px;
  color: #829497;
}

.breadcrumb b {
  color: #315a60;
}

.connection {
  color: #208d70;
  background: #eaf7f0;
  padding: 9px 13px;
  border-radius: 8px;
  font-size: 12px;
}

.connection.offline {
  color: #b27736;
  background: #fff5e7;
}

.content {
  max-width: 1550px;
  margin: 0 auto;
  padding: 30px 35px;
}

.hero {
  background: white;
  padding: 29px;
  border: 1px solid #e3ece8;
  border-radius: 16px;
}

.eyebrow {
  color: #24967e;
  font-size: 11px;
  font-weight: bold;
  letter-spacing: 2px;
}

.hero h1 {
  font-size: clamp(23px, 2.4vw, 32px);
  margin: 14px 0;
  color: #193f46;
  line-height: 1.45;
}

.hero p {
  color: #7b9093;
  margin: 0;
  font-size: 14px;
}

.notice {
  background: #e8f2fa;
  color: #53758f;
  border-radius: 9px;
  padding: 15px 18px;
  margin: 18px 0;
  font-size: 13px;
}

.notice b {
  margin-right: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: white;
  border: 1px solid #e3ebe7;
  border-radius: 14px;
  padding: 23px;
}

.stat-card span {
  color: #71888d;
  font-size: 12px;
}

.stat-card strong {
  display: block;
  font-size: 30px;
  margin: 13px 0;
  color: #153f47;
  font-weight: 700;
}

.stat-card small {
  color: #9aa9a9;
}

.main-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 18px;
}

.panel {
  background: white;
  border: 1px solid #e1ebe7;
  border-radius: 16px;
  padding: 22px;
  min-width: 0;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 22px;
}

.panel-heading h2 {
  margin: 0;
  color: #204850;
  font-size: 19px;
}

.panel-heading p {
  color: #90a1a3;
  font-size: 12px;
  margin: 8px 0 0;
}

.pill {
  background: #f0f4f2;
  padding: 7px 10px;
  border-radius: 7px;
  color: #687f80;
  font-size: 11px;
  white-space: nowrap;
}

.pill.green {
  background: #e8f6ed;
  color: #218d71;
}

.risk-item,
.project-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid #edf1ef;
}

.risk-icon,
.project-number {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 9px;
  background: #eef7f3;
  color: #2a927b;
  display: grid;
  place-items: center;
}

.risk-info,
.project-content {
  flex: 1;
  min-width: 0;
}

.risk-info strong,
.project-content strong {
  display: block;
  color: #31575d;
  font-size: 13px;
}

.risk-info small,
.project-content p {
  display: block;
  color: #91a0a1;
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
}

.risk-right {
  text-align: right;
}

.risk-right small {
  display: block;
  color: #8c9fa1;
  margin-top: 7px;
}

.risk-tag {
  padding: 4px 8px;
  border-radius: 6px;
  background: #edf5f0;
  color: #40886e;
  font-size: 11px;
}

.risk-tag.high {
  background: #fff0eb;
  color: #c66c54;
}

.budget-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.budget-title label {
  font-weight: 650;
  color: #31575d;
}

.budget-title strong {
  font-size: 26px;
  color: #218b71;
}

.budget-title small {
  font-size: 12px;
}

.budget-area input[type="range"] {
  display: block;
  width: 100%;
  margin: 25px 0 10px;
  accent-color: #249c80;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  color: #9aa9a7;
  font-size: 11px;
}

.action-button {
  display: block;
  width: 100%;
  background: #20987d;
  color: white;
  border: none;
  padding: 14px;
  border-radius: 10px;
  margin-top: 23px;
  cursor: pointer;
  font-weight: bold;
  font-size: 13px;
}

.action-button:hover {
  background: #187a66;
}

.action-button:disabled {
  opacity: .65;
  cursor: wait;
}

.result-bar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  background: #f0f8f4;
  padding: 16px;
  border-radius: 11px;
  margin-top: 21px;
}

.result-bar small {
  display: block;
  color: #718b83;
  margin-bottom: 8px;
}

.result-bar strong {
  color: #21866d;
}

.progress-track {
  background: #e5f0eb;
  height: 8px;
  border-radius: 10px;
  margin-top: 13px;
  overflow: hidden;
}

.progress-fill {
  background: #2bae8b;
  height: 100%;
  transition: width .3s;
}

.plan-heading {
  display: flex;
  justify-content: space-between;
  margin-top: 25px;
  font-weight: 700;
  color: #315b5c;
}

.plan-heading span {
  color: #94a5a4;
  font-weight: 400;
}

.project-content p {
  font-size: 11px;
}

.project-price {
  color: #4f7771;
  font-size: 12px;
  white-space: nowrap;
}

.panel-footnote {
  font-size: 11px;
  color: #9aa6a6;
  line-height: 1.7;
  margin-top: 18px;
}

.error-box {
  background: #fff0ed;
  color: #bd5848;
  border-radius: 9px;
  padding: 14px;
  margin: 15px 0;
  font-size: 13px;
}

.error-box button {
  margin-left: 12px;
  cursor: pointer;
}

.empty {
  padding: 25px 8px;
  color: #96a6a5;
  font-size: 13px;
}

.footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 26px;
  font-size: 11px;
  color: #a3b1b0;
}

@media (max-width: 1050px) {
  .sidebar {
    width: 195px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .shell {
    display: block;
  }

  .sidebar {
    width: 100%;
    padding: 16px;
  }

  .brand {
    margin-bottom: 15px;
  }

  .navigation {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .nav-label,
  .sidebar-bottom {
    display: none;
  }

  .topbar {
    padding: 0 16px;
  }

  .content {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-card strong {
    font-size: 23px;
  }

  .panel {
    padding: 16px;
  }

  .footer {
    flex-direction: column;
  }
}


/* 决策目标选择 */
.mode-picker {
  display: grid;
  gap: 10px;
  margin-bottom: 26px;
}

.mode-picker > strong {
  color: #31575d;
  font-size: 14px;
  margin-bottom: 3px;
}

.mode-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px;
  border: 1px solid #e0eae5;
  border-radius: 10px;
  cursor: pointer;
  background: #fff;
}

.mode-option:has(input:checked) {
  border-color: #24977d;
  background: #edf8f3;
}

.mode-option input {
  accent-color: #24977d;
  width: 17px;
  height: 17px;
}

.mode-option span {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.mode-option b {
  color: #284f53;
  font-size: 13px;
}

.mode-option small {
  color: #839b97;
  font-size: 11px;
}

/* 公平保障结果 */
.fairness-result {
  padding: 17px;
  border-radius: 11px;
  margin: 17px 0;
  background: #f1f8f4;
  border: 1px solid #d9ebe2;
}

.fairness-result strong {
  display: block;
  margin-bottom: 12px;
}

.fairness-result p {
  font-size: 13px;
  color: #557771;
  line-height: 1.6;
  margin: 7px 0;
}

.result-success {
  color: #188568;
}

.result-warning {
  color: #b47932;
}


/* 生活出行链推演区域 */
.mobility-section {
  margin-top: 22px;
  scroll-margin-top: 24px;
}

.mobility-empty {
  background: #ffffff;
  border: 1px solid #dfeae5;
  border-radius: 16px;
  padding: 35px;
  min-height: 160px;
}

.mobility-empty h2 {
  font-size: 21px;
  color: #244b51;
  margin: 0 0 15px;
}

.mobility-empty p {
  color: #819592;
  font-size: 14px;
  line-height: 1.8;
}

/* 最终参赛版：核心决策双栏布局 */
.main-grid {
  display: grid;
  grid-template-columns:
    minmax(0, 1.45fr)
    minmax(340px, 1fr);
  align-items: start;
  gap: 18px;
}

.main-grid .mobility-primary {
  min-width: 0;
  margin-top: 0;
}

.risk-section {
  margin-top: 22px;
  scroll-margin-top: 24px;
}

#mobility,
#planning {
  scroll-margin-top: 24px;
}

/* 中小屏幕上下排列 */
@media (max-width: 1120px) {
  .main-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

</style>