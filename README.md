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

```bash
pip install -e ".[test]"
pytest -q
uvicorn taxledger.api:create_app --factory --port 8000
```

企业试点使用 `.env.example`、`compose.yaml` 和 `docs/production-runbook.md`；首次启动由 Alembic 执行迁移。CI 同时验证 SQLite 工作流、迁移往返、PostgreSQL 精度/隔离和非 root 容器。

项目使用合成数据验证工程行为，不构成税务意见，也不声称未经客户验证即可直接用于法定申报。生产启用仍需税务规则、数据映射、安全与容量准入。
