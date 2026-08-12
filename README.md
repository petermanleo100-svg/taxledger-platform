# TaxLedger Platform

可直接部署企业试点的税务数据治理、VAT 勾稽与申报工作底稿平台。

## 已实现

- ERP 与发票数据标准化进入双轨税务台账，Decimal/Numeric 保证金额精度。
- 原始系统、字段映射、转换规则与内容哈希形成字段级血缘证据。
- 总账税额、发票池税额、申报税额三方勾稽及容差异常识别。
- 申报工作底稿版本、内容哈希、独立复核和乐观并发控制。
- 租户隔离、跨模块审计哈希链、FastAPI/OpenAPI、非 root 容器和 CI。
- JWT 角色权限与令牌租户绑定，拒绝客户端伪造租户上下文。
- PostgreSQL/Alembic、健康探针、请求追踪、安全响应头、Prometheus 指标与加固 Compose。
- PostgreSQL 强制 RLS、AES-256-GCM 加密备份、精确 Alembic 版本空库恢复与审计链验证。
- 2 MiB 请求限制、1000 条批量上限、统一数据库错误、结构化访问日志和管理员完整性接口。
- 生产默认 OIDC/JWKS（RS256/ES256、5 分钟密钥缓存）；HS256 仅允许显式受控例外。
- PostgreSQL advisory transaction lock 串行化每租户审计链，CI 执行 8 线程并发无分叉验证。
- 版本化 Prometheus 告警规则经 `promtool` 校验；容器 CI 生成 SPDX SBOM，并阻断已有修复的 Critical 漏洞。
- 手动发布候选保留镜像归档、校验和、SBOM 与 GitHub attestations；仅 `vX.Y.Z` 标签可发布带不可变摘要和来源证明的 GHCR 镜像。

```bash
pip install -e ".[test]"
pytest -q
uvicorn taxledger.api:create_app --factory --port 8000
```

企业试点使用 `.env.example`、`compose.yaml` 和 `docs/production-runbook.md`；迁移所有者与请求运行账号严格分离，API 启动前执行数据库角色、精确 Alembic 版本、强制 RLS、OIDC 与备份密钥准入检查。CI 同时验证 SQLite 工作流、迁移往返、PostgreSQL 精度/RLS/并发审计链/加密恢复、非 root 容器和完整 Compose 启动。

运维入口：`taxledger-operations backup-create <path>`、`backup-restore <path> --target-url <url>` 与 `audit-verify [--tenant ...]`。

项目使用合成数据验证工程行为，不构成税务意见，也不声称未经客户验证即可直接用于法定申报。生产启用仍需税务规则、数据映射、安全与容量准入。
