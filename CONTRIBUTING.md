# Contributing

## 目的
本仓库采用统一的分支、评审、CI 与本地运行规则，目标是：
- 降低误操作风险
- 防止红灯代码进入 `main`
- 提高多人协作稳定性
- 保证本地与 CI 的执行路径一致

---

## 强制协作规则（必须执行）

### 1. 开发前必须先同步主分支
任何开发开始前，必须先执行：

```bash
git checkout main
git pull origin main