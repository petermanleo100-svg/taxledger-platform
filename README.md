# TaxLedger Platform

独立的企业税务数据治理、VAT 勾稽与申报工作底稿平台。

## 已实现

- ERP 与发票数据标准化进入双轨税务台账，Decimal/Numeric 保证金额精度。
- 原始系统、字段映射、转换规则与内容哈希形成字段级血缘证据。
- 总账税额、发票池税额、申报税额三方勾稽及容差异常识别。
- 申报工作底稿版本、内容哈希、独立复核和乐观并发控制。
- 租户隔离、跨模块审计哈希链、FastAPI/OpenAPI、非 root 容器和 CI。

```bash
pip install -e ".[test]"
pytest -q
uvicorn taxledger.api:create_app --factory --port 8000
```

项目使用合成数据验证工程行为，不构成税务意见，也不声称真实申报准确率。
