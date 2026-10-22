# 银龄智城 V2：公网发布图文步骤（Windows / GitHub / Streamlit）

**重要**：`http://localhost:8501` 只代表自己电脑。本教程发布完成后才能得到别人也能打开的 `https://...streamlit.app` 网址。

## A. 保留旧数据，先在本机升级验证

1. Windows 桌面旧的 `silver_city` 文件夹先重命名为 `silver_city_old`，不要直接覆盖。
2. 将新 ZIP 解压后得到新的 `silver_city`。如果旧版有实地调查数据，可先备份旧版的 `data/problems.csv`，并确认表头与新版一致后再替换；绝对不要混淆模拟与真实数据。
3. 用 VS Code 的「文件 → 打开文件夹」打开新 `silver_city`。
4. VS Code 顶部「终端 → 新建终端」，Windows 选择 CMD。
5. 逐行执行：

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

6. 浏览器访问 `http://localhost:8501`，确认侧边栏出现 **④ 完整出行链 · 空间联动推演**。
7. 新开一个 VS Code 终端（保留网页的原终端运行），激活虚拟环境后执行：

```bat
python scripts/run_experiment.py
python scripts/run_spatial_experiment.py
```

8. 在 `outputs/results` 和 `outputs/charts` 检查 CSV 与 PNG。V2 共应有 **10 项基础测试**通过。

## B. 创建 GitHub 仓库

1. 打开 https://github.com/ ，注册或登录你自己的 GitHub 账户。这个步骤需要用户自行授权，其他人不能代你连接账号。
2. 右上角 **+ → New repository**；仓库名输入 `silver-city-demo-2026`。
3. 可先选 **Public**（方便直接发布，代码和提交的文件会公开）。如果代码尚未适合公开，可以选择 **Private**，再到 Streamlit 设置访问权限。
4. 点击 **Create repository**。
5. 在新仓库页面，点击 **uploading an existing file**；如果已有 README，则点击 **Add file → Upload files**。
6. **打开本机 `silver_city` 文件夹，在文件夹里面选择项目内容拖进浏览器上传区域**。切记上传后仓库根目录应该看到 `app.py` 和 `requirements.txt`，不是只看到外层 `silver_city` 文件夹。
7. 要上传：`app.py`、`requirements.txt`、`core/`、`pages/`、`data/problems.csv`、`scripts/`、`tests/`、`README.md`、`DEPLOY_GUIDE.md`、`.streamlit/config.toml`（若隐藏文件没有拖进去也不影响程序主体）。
8. **不要上传** `.venv`、`.git`、真实人脸照片、身份证、住户地址、API Key、私密文件。`uploads` 文件夹的内容不需要上传。
9. 页面下方填提交备注 `Add Silver City demo`，点击 **Commit changes** 或 **Propose changes**，必要时再合并到 `main`。
10. 回到仓库首页，确认 **`app.py`、`requirements.txt` 在仓库根目录**，`core` 和 `pages` 仍是文件夹。

GitHub 官方帮助：https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository

## C. 发布到 Streamlit Community Cloud

1. 浏览器打开 **https://share.streamlit.io/**，使用你的 GitHub 账户完成登录或授权。
2. 点击 **Create app**，选择 **Yup, I have an app**（不同版本界面文字可能略变）。
3. Repository 选择 `<你的GitHub用户名>/silver-city-demo-2026`。
4. Branch 选择 `main`。
5. Main file path 填入 **`app.py`**。只有在误上传为多层目录时才需要 `silver_city/app.py`，更建议调整目录结构。
6. App URL 可自行填写容易识别的英文名。这里只是例子，是否可用由实际页面检查。
7. 可在 Advanced settings 中选择 Python 3.11。无特殊密钥时不要填写 Secrets。
8. 点击 **Deploy**，使用 Cloud logs 排查启动报错。成功后得到实际的网址 `https://<实际生成的名称>.streamlit.app`。
9. 在 **App settings → Sharing** 将演示程序设为 **public**（如果页面本来已经公开，则无需修改）。
10. 复制 **实际获得的链接**，在手机上断开 Wi-Fi、改用手机数据测试；同时请一位队友在另一台电脑测试。若境内学校网络无法稳定加载，保留离线演示视频和现场本地运行方案。

Streamlit 官方文档：
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app

## D. 公网部署后，必须知道的三个限制

1. **用户在网页新填的问题与照片只存储在当前浏览器会话中**，不会保存到 GitHub，也不会共享给其他访问者。必要时用「导出全部问题 CSV」在本地保存；跨访客协作需要另外接真正的数据库与登录授权。
2. **所有地图点位和社区路径均为演示模拟数据**，不能宣称这是实测社区的真实出行障碍。公共网站不要收集真实个人数据。
3. 免费 Community Cloud 可能休眠、资源受限；也不能保证本地 CSV 被永久保存。正式竞赛必须准备离线视频和本地演示版本。

## E. 让评委看到竞争力而不是普通表单

演示操作：
1. 页面③ 5万元展示传统收益组合。
2. 页面④ 同一预算比较普通评分最大化与空间联动优化。
3. 点击虚拟地图的红色阻断段，解释为什么一处台阶可能使完整生活链路不可通行。
4. 切换预算 3 → 5 → 10 → 15 万元，展示模拟可达出行链 2/9 与不同方案之间的差异。
5. 运行 `python scripts/run_spatial_experiment.py`，展示可复现的表格、图表和空间权重敏感性实验。
6. 说明路网/成本/权重是模拟值，下一阶段需要实地人行道拓扑与老年用户参与验证。

**版权与使用边界：** 当前版本是教学用工程原型，不含自动图像识别。不要用“已实现多模态AI自动体检”或“真实社区通行改善率”为它宣传。
