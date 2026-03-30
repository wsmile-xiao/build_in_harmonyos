# {软件名} {版本} 编译进度

> 本文件是编译过程的"黑匣子飞行记录器"。每个有意义的进展都应立即记录。
> **会话中断时，下一个会话应先读本文件恢复进度。**

## 当前状态
- **阶段**：Phase 1.5 / 2 / 3 / 4
- **更新时间**：YYYY-MM-DD HH:MM（每次修改都更新）
- **源码路径**：（编译目录的完整路径）
- **原始源码路径**：（原始 tarball 解压后的路径，用于 diff 校验）

## ⚠️ 致命约束速查（每次阶段转换时检查）

> **上下文压缩后请重新读取此清单。这些约束违反一次就造成不可逆损失。**

- [ ] **D1 补丁完整性**：Phase 4 前 `diff -ruN original/ modified/` 校验所有源码修改
- [ ] **D2 知识校准**：Phase 4 Step 6 不是全量复盘，而是校验+补充
- [ ] **D3 索引同步**：归档后运行 `aggregate-index.sh` + `gen_summary.py`
- [ ] **D4 模板一致性**：init-archive.sh 必须使用 `templates/PROGRESS.md`
- [ ] **D5 测试前置**：弹窗预确认 + `MAKEFLAGS=-j1` + `timeout 1800`（或运行 `prep-test.sh`）
- [ ] **D6 临时文件清理**：Phase 4 前清理 DIAGNOSIS_*.md / MISSING_*.md 等临时文件
- [ ] **D7 四维度完成度**：编译产出 + 补丁完整性 + 知识提取 + 索引同步

## 🔴 严重约束速查（编译过程中遵守）

> **这些约束违反会导致编译失败或产物不可用。**

- [ ] **S1 软链接**：禁止 `ln -sf` 覆盖，必须 `rm -f` + `ln -s`；不可用则用 wrapper 脚本
- [ ] **S2 ELF 签名**：修改 ELF 后必须重新签名（`sign-elf.sh`），否则 Permission Denied
- [ ] **S3 知识证伪**：发现与 knowledge/ 矛盾 → 立即标注 `DEPRECATED` 并更新
- [ ] **S4 Phase 1.5 不可跳过**：骨架先于编译，否则无处记录
- [ ] **S5 /tmp 不可写**：必须 `export TMPDIR=$HOME/tmp`
- [ ] **S6 弹窗确认**：首次运行新二进制会弹出 30 秒确认框，测试前预触发
- [ ] **S7 实时知识提取**：Phase 3 每步完成后立即判断 L1/L2/L3，禁止批量补记
- [ ] **S8 补丁编号连续**：NNNN 必须连续，刷新时用 `refresh-patch.sh`
- [ ] **S9 PR 不改公共文件**：工作分支禁止修改 `_index.yaml` 和 `SUMMARY.md`

## 🧭 问题→知识文件导航（遇到问题时查阅）

> **不要记住 24 个文件名，记住这 8 个问题分类。遇到问题直接查对应文件。**

| 遇到什么问题 | 查什么文件 | 关键搜索 |
|------------|-----------|---------|
| 编译报错不知怎么分析 | `debug-methodology.md` | 先看 §1 决策树，按阶段排查 |
| 看到一个具体错误信息 | `error-patterns.md` | `grep "错误关键词" knowledge/error-patterns.md` |
| SELinux/签名/软链接/弹窗/权限 | `harmonyos-specifics.md` | §7 子进程 §9 软链接 §11 签名 |
| /tmp/TMPDIR/环境变量 | `environment.md` | §6 TMPDIR §9 软链接 §15 测试 |
| 函数不存在（musl vs glibc） | `musl-compat.md` | `grep "函数名" knowledge/musl-compat.md` |
| configure/cmake 参数怎么设 | `build-systems.md` | 查构建系统的"推荐参数"章节 |
| autotools 宏需要 patch | `autotools-patterns.md` | config.guess/config.sub 常见修复 |
| 缺少依赖库/编译顺序 | `dependency-resolution.md` | §3 判断标准 §6 隔离环境 |
| 打包/RPATH/strip/签名流程 | `packaging.md` | §2 七步签名流程 |
| 发布/install.sh/uninstall.sh | `release.md` | §3 打包流程 §4 模板规范 |

## 🔧 工具速查

> **不确定具体步骤时，调用工具脚本代替手动操作。**

| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `init-archive.sh <名> <版本>` | Phase 1.5 骨架创建 | 确定编译方案后立即执行 |
| `check-env.sh` | Phase 2 环境检查 | 编译前 |
| `detect-build-system.sh <源码>` | Phase 3 识别构建系统 | 进入编译阶段 |
| `sign-elf.sh` | ELF 签名四步 | 修改 ELF 后 |
| `verify-symlinks.sh` | 验证软链接 | make install 后 |
| `refresh-patch.sh` | 补丁刷新（三目录法） | Phase 4 补丁生成 |
| `prep-test.sh` | 测试前置三步 | make check 前 |
| `check-knowledge-gap.sh` | 知识遗漏校验 | Phase 4 收尾 |
| `close-archive.sh` | 归档收尾 | Phase 4 最后一步 |
| `aggregate-index.sh` | 生成 _index.yaml | PR 合并时 |
| `validate-patch.sh` | 验证补丁可应用 | 补丁生成后 |

## 检索结果（Phase 1）
- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"
- **精确匹配**：有 / 无
  - 档案路径：archives/...
  - 复用方案：...
- **相似版本**：有 / 无
  - 版本：...
  - 补丁可复用性：...
- **knowledge/ 检索**：
  - 相关错误模式：E0XX
  - 相关知识文件：...

## 环境准备（Phase 2）
- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"
- [x] / [ ] 环境变量已检查
- [x] / [ ] 依赖工具已验证
- [x] / [ ] 骨架目录已创建
- **问题记录**：（Phase 2 中遇到的问题，如有）

## 编译过程（Phase 3）

- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"
- **构建系统**：autotools / cmake / meson / makefile / custom
- **实际执行的配置命令**：（如 `./configure --prefix=... ...`）

### 错误 1：{简短标题，如 "config.guess 无法识别系统"}
- **阶段**：configure / compile / link / install / test
- **错误信息**：（关键行）
- **根因分析**：
- **解决方案**：
- **跨软件通用性评估**：
  - [ ] ✅ 是 — 其他软件也会遇到（原因：...）
  - [ ] ❌ 否 — 仅本软件特有（原因：...）
  - [ ] ⏳ 待评估
- **知识库更新状态**：
  - [ ] 已更新 knowledge/xxx.md（描述更新内容）
  - [ ] 未更新（原因：仅本软件相关 / 待 Phase 4 评估）

### 错误 2：...

## 源码修改清单

- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"

> ⚠️ Phase 4 归档前必须用此清单做 diff 校验，确保零遗漏。

| # | 文件 | 修改原因 | 补丁编号 | 补丁状态 |
|---|------|---------|---------|---------|
| 1 | src/foo.c | 修复 XXX | 0001 | ✅ 已生成 |
| 2 | configure.ac | 添加 OHOS | 0002 | ✅ 已生成 |
| 3 | Makefile.am | 禁用 XXX | — | ⏳ 未生成补丁 |

## 测试结果（Phase 4）
- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"
- **测试类型**：official / manual / skipped
- **结果概要**：passed X / failed Y / skipped Z
- **失败分析**：（编译问题 vs 环境兼容性问题）

## 待办清单

- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"

> Phase 4 归档前必须逐项确认。

- [ ] 补丁完整性校验（diff 比对原始源码）
- [ ] 补丁可干净应用验证（patch --dry-run）
- [ ] manifest.yaml 创建且字段完整
- [ ] README.md 编写
- [ ] PROGRESS.md 中"⏳ 待评估"条目已全部处理
- [ ] knowledge/ 文件已更新所有 L1/L2 知识
- [ ] SUMMARY.md 已重新生成（gen_summary.py）
- [ ] _index.yaml 已同步

## 会话恢复指南

- **压缩恢复**：如果刚经历上下文压缩，重新读取 `KNOW_YOUR_WHY.md` 并检查上方"致命约束速查"

> 如果会话中断，下一个会话应：
> 1. 读取本文件的"当前状态"确定中断位置
> 2. 从"待办清单"中找到未完成项
> 3. 从"源码修改清单"中确认已做的修改（即使没生成补丁）
> 4. 继续 Phase 3 或 Phase 4

