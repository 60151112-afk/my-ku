# A股量化私有管理后台

这个后台用于本人管理选股、公开快照和 GitHub Pages 发布流程。它不是公开只读网站，不应无密码暴露。

## 本地启动

PowerShell:

```powershell
$env:PUBLIC_DASHBOARD_ADMIN_PASSWORD="change-this-password"
scripts\run_public_dashboard_admin.ps1
```

打开 `http://localhost:8505`。

## 权限边界

- 后台只调用白名单命令；
- 不支持任意 shell 输入；
- 不连接券商；
- 不自动下单；
- 推送公网需要额外设置 `PUBLIC_DASHBOARD_ADMIN_ALLOW_PUSH=1`。

## 公网部署建议

如果部署到云服务器，至少要同时满足：

- 设置强密码或 `PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256`；
- 使用 HTTPS；
- 服务器层增加 Basic Auth、Cloudflare Access 或 VPN；
- 不把 `.env`、券商配置、`data/` 和完整输出缓存放到公开仓库。
