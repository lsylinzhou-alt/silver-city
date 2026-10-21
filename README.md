# 银龄智城 · 四天冲刺版

这是教学与竞赛演示原型，不是已经部署的城市治理系统。

## Windows（VS Code终端请选择「命令提示符」）

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

若 Windows 无 `py -3.11`，在确认已经安装 Python 3.11 后尝试 `python -m venv .venv`。

## macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

浏览器访问终端输出地址，一般是 http://localhost:8501 。按 Ctrl+C 结束运行。

## 生成实验文件

```bash
python scripts/run_experiment.py
```

输出目录：`outputs/results/` 与 `outputs/charts/`。

## 数据与伦理

初始 `data/problems.csv` 文件由程序自动生成，全部是**模拟数据**，位置、成本、风险等均不代表真实社区。系统默认的地图位置不是实地调查成果；照片只是人工核验的依据，不是AI自动识别。评分权重未校准，优化分数并非真实惠及人口、工程效果或政策建议。不得上传可识别居民个人的信息。

**建议参赛题名**：《银龄智城——基于多源空间数据与预算约束优化的社区适老化数字体检与微更新决策系统》。如未实现真正自动视觉识别，不应声称已实现多模态AI自动体检。
