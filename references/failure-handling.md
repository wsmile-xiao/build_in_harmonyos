> 本文件从 SKILL.md v4.8 提取，详细内容供按需加载。

# 失败处理标准流程（R11 + R12 强制执行）

来源: SKILL.md §1.2（失败处理标准流程完整版）

> **任何脚本步骤失败或编译错误触发时，必须按以下顺序执行。跳过任何一步都是 bug。**

---

## R11: 三步查归档记录流程

```
[R11] 第一步：查归档记录
  │
  ├─ ① 读 archives/{pkg}/{ver}/README.md
  │    → 已有完整方案？（补丁/特殊构建方式/gen-all.pl 等）
  │    → 有 → 直接使用历史方案重新执行
  │    → 无 → 继续 ②
  │
  ├─ ② 读 archives/{pkg}/{ver}/manifest.yaml
  │    → status in ("published", "built")？说明之前成功过，对比差异
  │    → patches_applied 有补丁？确认是否已正确应用
  │    → knowledge_gained 有经验？参考历史做法
  │
  └─ ③ 读 archives/{pkg}/README.md（软件级）
       → 其他版本的通用经验（如 automake 的鸡生蛋问题）
```

### R11 详解

- **步骤 ①**：版本级 README.md 通常包含该版本的完整编译方案，包括需要的特殊构建方式（如 automake 的 `gen-all.pl` 鸡生蛋绕过）
- **步骤 ②**：manifest.yaml 中的 `status` 字段可判断历史是否成功；`patches_applied` 列出已用补丁；`knowledge_gained` 记录经验
- **步骤 ③**：软件级 README.md 包含跨版本的通用经验，适用于同软件不同版本遇到类似问题

---

## R12: 五阶段引擎匹配流程（⭐ v4.8 升级）

```
[R12] 第二步：匹配错误模式（⭐ 使用知识图谱引擎）
  │
  ├─ ① **引擎匹配**（推荐，v4.8+）
  │    → 从错误日志提取关键词
  │    → Phase A: grep 关键词于 graph/index.tsv → 候选集
  │    → Phase B: 加载候选 graph/E*.kv → error_signature 精确匹配
  │    → Phase C: 读取 rec_*/forbid_*/fallback_* 方案
  │    → Phase D: principles 原则过滤
  │    → Phase E: 输出结构化修复方案
  │    → 命中？→ 直接用推荐方案修复 ✅
  │
  ├─ ② 快速查找（备选）
  │    → grep -i "关键词" knowledge/graph/index.tsv
  │    → 找到 E 编号 → 读 knowledge/doc/E{NNN}.md
  │
  └─ ③ 人类浏览（备选）
       → 阅读 knowledge/error-patterns.md 总览表
       → 按 E 编号查找对应条目

  └─ ② 搜索同类软件的 manifest.yaml（同 build_system）
       → autotools 项目怎么处理的？→ 参考其 configure 参数
       → 同类错误别人怎么修的？→ 直接复用方案
```

### 五阶段引擎匹配详解

| 阶段 | 输入 | 处理 | 输出 |
|------|------|------|------|
| **Phase A: 粗筛** | 错误日志关键词 | grep 全量扫描 `graph/index.tsv` keywords 列 | 候选集：{E075, E032, E033} |
| **Phase B: 精排** | 候选集 .kv 文件 | 加载候选 graph/E*.kv，`error_signature` 正则精确匹配 | 命中条目：E075 |
| **Phase C: 方案生成** | 命中条目 | 读取 `rec_*`/`fallback_*`/`forbid_*` 字段 | 推荐方案 + 回退方案 + 禁止事项 |
| **Phase D: 原则过滤** | 推荐方案 | 检查 `principles` 引用是否与当前上下文冲突 | 通过/冲突 |
| **Phase E: 输出执行** | 过滤后方案 | 返回结构化方案给 AI 或 `auto_fix_impl` 自动执行 | `{ approach, command, forbid, auto_fix }` |

---

## 完整流程（R11 → R12 → 动手修复）

```
脚本/编译步骤失败
  │
  ├─ [R11] 查归档记录（三步）
  │   → 找到方案？→ 直接复用 ✅
  │   → 未找到 → 继续 R12
  │
  ├─ [R12] 匹配错误模式（五阶段引擎）
  │   → 命中？→ 用推荐方案修复 ✅
  │   → 未命中 → 搜索同类软件 manifest
  │
  └─ [诊断完成] 基于历史方案动手修复
      → 如果归档和知识库都没有 → 记录为新问题（§2.5 实时知识提取）
      → 修复后更新 notes.md + 继续执行
```

---

## automake 反面案例 vs 正确流程对比

### ❌ 反面案例（automake 会话实录）

```
❌ build-driver Step 3 失败（unknown build system）
   → 放弃 build-driver，手动 ls 目录找 configure
   → 手动跑 configure → config.guess 不识别
   → 从 GNU FTP 下载最新版 → 还是不识别
   → 试 --build 参数 → 用户杀掉进程
```

**问题分析**：
1. 跳过了 R11（没查归档），不知道已有完整方案和补丁
2. 跳过了 R12（没查错误模式），不知道 config.guess 不识别是 E002 标准问题
3. 凭直觉试错（下载新版、加 --build 参数），越陷越深
4. 最终用户失去耐心杀掉进程

### ✅ 正确流程（遵循 R11+R12）

```
   → build-driver Step 3 失败
   → [R11] 读 archives/a/automake/1.16.5/README.md
      → 发现：需要 gen-all.pl 鸡生蛋绕过 + 已有补丁
   → [R11] 读 manifest.yaml → status=published, 有 0001-port-for-ohos.patch
   → [R12] 错误是 config.guess 不识别 → E002 标准解法：应用已有补丁
   → 应用补丁后重新跑 build-driver → 通过
```

**关键差异**：正确流程利用历史归档中的完整方案，直接复用已知补丁，无需任何试错。

---

## R14 补充：脚本失败后的行为规范

> **R14**: 脚本失败=手动模式入口，非终止。

| 场景 | ❌ 错误行为 | ✅ 正确行为 |
|------|-----------|-----------|
| build-driver 失败 | AI 放弃，什么都不做 | 按 R11+R12 诊断，手动执行对应步骤 |
| 手动步骤完成后 | 停在手动模式 | `--resume-from=StepN` 继续自动流程 |
| 所有脚本都失败 | 彻底放弃 | 记录到 notes.md，标记 failed，执行 finish-build |
