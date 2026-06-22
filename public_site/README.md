# A股量化研究公开看板

这个目录是公网只读版本。不要把 `quant_trader/china_stock_dashboard.py` 直接部署到公网，因为本地研究面板包含刷新、诊断、文件路径和本机命令等能力。

公开版只读取 `public_site/public_data/dashboard_public_latest.json`，该文件由导出器脱敏生成，不包含券商连接、自动下单或本机执行命令。

## 本地生成公开数据

在项目根目录运行：

```powershell
python -m quant_trader.public_dashboard_export --project-root . --output public_site\public_data\dashboard_public_latest.json
```

或使用脚本：

```powershell
scripts\export_public_dashboard.ps1
```

## 本地预览

```powershell
streamlit run public_site\app.py --server.port 8503
```

浏览器打开 `http://localhost:8503`。

## 部署到任何人可访问的网站

推荐把 `public_site/` 作为独立 Streamlit 应用部署到云服务器、Streamlit 托管平台或 Hugging Face Spaces。公网部署时只上传 `public_site/`、`public_site/public_data/dashboard_public_latest.json` 和依赖文件，不上传本机 `data/`、`outputs/`、`.env` 或券商配置。

云服务器示例：

```bash
pip install -r public_site/requirements.txt
streamlit run public_site/app.py --server.address 0.0.0.0 --server.port 8503
```

如果需要绑定域名，使用 Nginx 或平台自带域名把外部流量转发到 Streamlit 端口。

## 更新流程

1. 本地运行原研究面板或策略程序，生成最新诊断和复盘输出。
2. 运行公开数据导出命令，刷新 `dashboard_public_latest.json`。
3. 将 `public_site/public_data/` 的新快照同步到部署平台。

公开网页仅用于研究展示，不构成投资建议。

## 一键更新公网版本

仓库绑定 GitHub 后，日常更新公网网页优先使用：

```powershell
scripts\update_public_dashboard_and_push.ps1
```

该脚本会执行：

- 生成脱敏公开快照；
- 校验公开目录没有本机路径、命令或密钥类敏感内容；
- 运行公开导出单元测试；
- 只暂存公开网站白名单文件；
- 提交并推送到 `main`，随后 GitHub Actions 自动刷新 `gh-pages`。

只做本地校验不提交：

```powershell
scripts\update_public_dashboard_and_push.ps1 -ValidateOnly -SkipExport
```

## 纯静态部署

如果目标是“任何人打开链接都能访问”，优先使用纯静态入口：

- `public_site/index.html`
- `public_site/public_data/dashboard_public_latest.json`
- `public_site/public_data/dashboard_public_summary.csv`
- `public_site/.nojekyll`

本地预览：

```powershell
python -m http.server 8504 -d public_site
```

浏览器打开 `http://localhost:8504`。

部署到 GitHub Pages 时，把 `public_site/` 作为站点目录发布即可。静态版不需要 Python、Streamlit、服务器进程或券商配置。

## GitHub Pages 自动发布

仓库已提供 `.github/workflows/deploy-public-dashboard.yml`。该工作流会把 `public_site/` 中的静态站点发布到 `gh-pages` 分支。

1. 把本项目推送到 GitHub 仓库。
2. 在 GitHub 仓库页面打开 `Settings -> Pages`。
3. `Build and deployment` 选择 `Deploy from a branch`。
4. `Branch` 选择 `gh-pages`，目录选择 `/root`，点击 `Save`。
4. 本地刷新公开快照并校验：

```powershell
scripts\build_public_dashboard_static_package.ps1
scripts\validate_public_dashboard_static_site.ps1
```

5. 提交并推送 `public_site/`、`.github/workflows/deploy-public-dashboard.yml` 和脚本变更。

推送到 `main` 或 `master` 后，GitHub Actions 会自动刷新 `gh-pages` 分支。Pages 启用后，公网地址通常是：

```text
https://<your-user>.github.io/<your-repo>/
```

如果仓库没有绑定 GitHub 远程地址，先执行：

```powershell
git remote add origin https://github.com/<your-user>/<your-repo>.git
```

然后再推送分支。不要上传本机 `data/`、`outputs/`、`.env` 或券商配置。
