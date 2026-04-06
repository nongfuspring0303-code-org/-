# Contributing

## 目的
本仓库采用统一的分支、评审、CI 与本地运行规则，目标是：
- 降低误操作风险
- 防止红灯代码进入 `main`
- 提高多人协作稳定性
- 保证本地与 CI 的执行路径一致

---

## 分支与提交规则

### 1. 所有改动必须先从 `main` 拉取最新
开始任何开发前，先同步最新主分支：

```bash
git checkout main
git pull origin main