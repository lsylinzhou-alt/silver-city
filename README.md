# 银龄智城 · 竞赛增强演示版 V3

面向研究生智慧城市竞赛的可运行 Streamlit 原型。**默认数据是合成的演示数据，空间网络也经过人工构造，并非实测的真实社区路网。**

## 五个功能页面

1. **问题采集**：人工录入位置、问题、证据和费用；浏览器会话内保存、可导出 CSV。
2. **数字体检**：风险分与相对风险地图，来源与人工核验标注。
3. **微更新决策**：预算组合优化、基线比较、权重敏感性。
4. **出行链与空间推演**：三栋假设住宅到卫生站、菜市场、公交站的 9 条出行链；比较传统收益优化与“收益 + 路线可达性”双目标方案，以及不同预算的通达变化。

5. **片区路网与人群差异**：可上传自己调查的节点/道路/项目CSV，按通行档案区分可达路段，比较传统收益优化与出行链+弱覆盖楼栋协同优化；输出项目的链路边际解释。

这不是完整的街景 AI 检测，也不能代替工程安全评估。新增加的 `core/mobility.py` 是**方法概念验证**，真实应用必须接入真实人行道数据和实测通行约束。

## 在 Windows VS Code CMD 终端运行

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

浏览器打开 `http://localhost:8501`。

## 输出对比实验

```bat
python scripts/run_experiment.py
python scripts/run_spatial_experiment.py
python scripts/run_network_experiment.py
```

输出 `outputs/results/` 中的 CSV 和 `outputs/charts/` 中的 PNG。

## 公网发布

已部署用户请优先阅读 [竞赛升级_逐步操作.md](竞赛升级_逐步操作.md)；初次部署用户再阅读 [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)，其中包含 GitHub 仓库上传、Streamlit Community Cloud 部署、设为公开、手机测试、数据安全与备份步骤。

**重要**：新增问题/上传照片仅在当前浏览器会话暂存，不对公众提供永久数据服务。公共部署时，初始模拟数据为只读文件。不能上传居民个人隐私。
