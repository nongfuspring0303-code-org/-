---
title: Contract Versioning & Compatibility
title_zh: 合同版本控制与兼容性
version: v1.0
status: appendix_normative
parent_doc: 主题板块催化持续性引擎 v1.0
---

# Contract Versioning & Compatibility｜合同版本控制与兼容性

## 1. 目的

定义契约如何演进，避免：
- 字段偷偷新增
- 字段语义漂移
- 下游无感 breaking change

## 2. 版本字段

所有 schema / 输出对象必须包含：

```yaml
contract_name:
contract_version:
producer_module:
```

实现口径：
- 允许业务对象保持最小字段集。
- 但在统一下发前，必须由输出信封补齐 `contract_name/contract_version/producer_module`。
- 下游兼容判定以“输出信封”中的契约字段为准。

## 3. 变更类型

### 非破坏性变更
- 新增可空字段
- 新增枚举但下游不依赖穷举
- 新增附加说明字段

### 破坏性变更
- 删除字段
- 修改字段语义
- 修改字段类型
- 修改枚举含义
- 修改缺省行为

## 4. 兼容窗口

- 非破坏性变更：可直接进入次版本
- 破坏性变更：必须至少保留一个兼容窗口
- 推荐窗口：`1 minor version`

## 5. 流程

1. 提出变更
2. 标注 breaking / non-breaking
3. 更新主文档
4. 更新 schema
5. 更新 consumer mapping
6. 完成 E2E 验收
7. 才能合并

## 6. 一句话裁决

> 契约升级必须带版本、带兼容窗口、带迁移路径。
