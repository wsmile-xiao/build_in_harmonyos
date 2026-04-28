# 贡献指南

> 如何为鸿蒙编译知识库添加新软件或改进现有内容。
> 对齐 SKILL.md v7.2 · 多 Agent 协作模式

## 目录

- [角色与权限](#角色与权限)
- [添加新软件](#添加新软件)
- [依赖管理](#依赖管理)
- [提交工作成果](#提交工作成果)
- [主编审核](#主编审核)
- [归档目录结构](#归档目录结构)
- [补丁规范](#补丁规范)
- [预编译包制作](#预编译包制作)
- [install.sh 规范](#installsh-规范)
- [manifest.yaml 字段](#manifestyaml-必填字段)
- [知识库更新](#知识库更新)

---

## 角色与权限

本项目采用 **协作者 / 主编** 双角色模式，通过 **Git 分支 + GitCode PR** 协作。

| 操作 | 协作者 | 主编 |
|------|--------|------|
| 编译软件 (`init-build`, `build`) | ✅ | 不做 |
| 知识图谱草稿 (`graph add --draft`) | ✅ | 不做 |
| 创建分支、推送、创建 PR | ✅ | 不做 |
| 合并 PR / 拒绝 PR（GitCode 平台） | ❌ | ✅ |
| 本地审核 (`review`) | ❌ | ✅ |
| 修改 index.tsv / SUMMARY.md | ❌ 禁止 | ✅（合并 PR 时自动） |
| 修改 SKILL.md / references / templates / scripts | ❌ 禁止 | ✅ |

**身份声明**：
```bash
# 协作者（默认，可省略）
export OHC_AGENT_ID="A7F3"    # 4 位十六进制随机 ID

# 主编
export OHC_ROLE=editor
export OHC_AGENT_ID="EDIT"
```

详细协作规范见 [knowledge/collaboration.md](knowledge/collaboration.md)，提交教程见 [knowledge/collaboration-tutorial.md](knowledge/collaboration-tutorial.md)。

---

## 添加新软件

### 方式 A：使用 SKILL 编译管线（推荐）

SKILL.md v7.2 定义了标准编译管线：

```
Step 1:  ohc-run.py init-build          初始化（下载/解压/骨架/依赖检查）
Step 2:  AI 编译                 configure + make + make install
Step 2.5: 独立目录安装验证       干源码 + 补丁 + 独立 TEST_PREFIX
Step 3:  make check / 功能验证   测试套件或手动功能测试
Step 4:  ohc-run.py verify-build         质量门禁（G1-G4 四道检测）
Step 5:  预编译包制作            9 步打包流程
Step 5.5: ohc-run.py finalize-archive    归档收口
Step 6:  ohc-run.py submit              提交工作成果
```

一键启动：

```bash
./scripts/ohc-run.py init-build <软件名> <版本> [--url=<下载URL>]
# 然后 AI 执行 Step 2 ~ Step 5.5
./scripts/ohc-run.py finish <软件名> <版本> success
# 提交成果
./scripts/ohc-run.py submit <软件名> <版本>
```

### 方式 B：手动创建档案

如果不用 ohc-run.py init-build，手动按以下步骤：

#### 1. 创建目录结构

```bash
mkdir -p archives/{首字母}/{软件名}/{版本}/{patches,reports,packaging}
```

**双层结构**（v4.0 强制）：

```
archives/{首字母}/{软件名}/          ← 软件级（跨版本共享）
├── README.md                        # 编译说明
├── RELEASENOTE.md                   # 发布说明（多版本聚合，自动生成）
│
└── {版本}/                          ← 版本级（每次编译快照）
    ├── manifest.yaml                # 元数据
    ├── PROGRESS.md                  # 进展记录
    ├── patches/                     # 补丁文件
    │   ├── 0001-xxx.patch
    │   └── 0002-yyy.patch
    ├── reports/                     # 报告
    │   ├── test-report.md
    │   ├── quality-report.md
    │   └── skill-feedback.md
    └── packaging/                  # 预编译包
        ├── {name}-{ver}-ohos-aarch64.tar.gz        # Release 包
        └── {name}-{ver}-ohos-aarch64-debug.tar.gz  # Debug 符号包
```

#### 2. 填写 manifest.yaml

见下方 [manifest.yaml 必填字段](#manifestyaml-必填字段)。

#### 3. 生成补丁

```bash
# 使用 ohc-run.py refresh-patch 自动生成（推荐）
./scripts/ohc-run.py refresh-patch --auto <软件名> <版本>

# 或手动生成
diff -Naur original/ modified/ > patches/0001-description.patch
```

#### 4. 验证

```bash
# 质量门禁
./scripts/ohc-run.py verify-build <软件名> <版本>

# 归档收口（自动清理+校验+生成 RELEASENOTE）
./scripts/ohc-run.py finalize-archive <软件名> <版本>
```

---

## 依赖管理

### 自动依赖解析

`init-build` 在 Step 7 自动检查编译所需的依赖。如果有预编译包可用（来自 [cmd-pkgs](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)），自动安装。

```bash
# 查看某软件缺少哪些依赖
./scripts/ohc-run.py resolve-deps wget
# 输出: 可安装: openssl 1.1.1w, zlib 1.3.1

# 自动安装缺失依赖
./scripts/ohc-run.py resolve-deps --install wget

# 列出所有可用预编译包（23 款）
./scripts/ohc-run.py resolve-deps --list-available

# 从远程仓库刷新索引
./scripts/ohc-run.py resolve-deps --refresh
```

### 手动安装预编译包

如果不想用 resolve-deps，也可以手动安装：

```bash
# 通用格式
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/{软件名}/install.sh" | sh -s -- {版本}

# 示例
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- openssl 1.1.1w
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- readline 8.2
```

### 依赖编译顺序

当预编译包不可用时，按 `knowledge/operations/dependencies.md` 中的顺序手动编译。常见链路：

```
基础: pkg-config → zlib → bzip2 → xz → openssl
扩展: ncurses → readline → bash
Python: openssl + zlib + libffi + ncurses + readline + gdbm + xz + bzip2 → python
```

---

## 提交工作成果

### 协作者提交流程（Git + GitCode PR）

编译完成并通过质量门禁后，通过 Git 分支 + GitCode Pull Request 提交工作成果：

#### Step 1：自检

```bash
# 本地验证（不实际提交，只检查完整性）
./scripts/ohc-run.py submit --check <软件名> <版本>
```

#### Step 2：创建分支

```bash
# 分支命名格式: {type}/{software}-{version}
# type: feat（新增）/ fix（修复）/ update（更新）
git checkout -b feat/<软件名>-<版本>
```

#### Step 3：暂存文件

```bash
# 添加相关文件到暂存区
git add archives/<首字母>/<软件名>/<版本>/
git add knowledge/graph/draft/        # 知识图谱草稿（如有）
```

#### Step 4：提交

```bash
# 提交信息可自由填写，PR 合并时会 Squash 为一条
git commit -m "feat(<软件名>): <版本> 编译完成"
```

#### Step 5：同步最新

```bash
# 确保基于最新 main 分支
git rebase main
```

#### Step 6：推送

```bash
git push origin feat/<软件名>-<版本>
```

#### Step 7：在 GitCode 创建 Pull Request

在 GitCode 平台上创建 PR，格式要求：

- **标题**：`feat(<软件名>): <版本> 编译完成` 或 `fix(<软件名>): <版本> 修复描述`
- **描述三要素**：
  1. **变更内容**：新增/修改了哪些文件（archives/、knowledge/graph/draft/ 等）
  2. **质量状态**：质量门禁结果（verify-build 通过 / 跳过原因）
  3. **特殊说明**：补丁说明、依赖变更、已知问题等

### 提交自检 12 项

提交前 `submit --check` 会自动检查：

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | 补丁完整性 | patches/ 目录有实际 .patch 文件 |
| 2 | manifest.yaml | status / software / version / build_system 等字段齐全 |
| 3 | 禁止文件 | 无 .o / .lo / .la / Makefile 等构建残留 |
| 4 | PROGRESS.md | 已关闭（status != in_progress） |
| 5 | 临时文件 | 无 *.tmp / *.bak / *.orig |
| 6 | knowledge_ref | 引用的 E 编号在 graph/ 中存在 |
| 7 | 打包产物 | packaging/ 有 tar.gz 产物 |
| 8 | test_results | manifest 中测试结果已填写 |
| 9 | 草稿冲突 | draft/ 中的 E 编号不与正式冲突 |
| 10 | 知识去重 | 草稿关键词不与已有条目重复 |
| 11 | 提交自检 | submission.yaml 格式正确 |
| 12 | 总体评估 | 综合判定 |

### 知识图谱草稿

编译过程中积累的经验以草稿形式提交：

```bash
# 添加知识草稿
./scripts/ohc-run.py graph add --draft \
  --title "openssl 1.1.1w configure 检测问题" \
  --error-pattern "cannot detect aarch64-unknown-linux-ohos" \
  --solution "替换 config.guess + config.sub → E007" \
  --match-keywords "config.guess,platform detect,ohos triplet"
```

草稿写入 `knowledge/graph/draft/`，随 PR 一起提交，主编合并 PR 时自动移入正式目录。

---

## 主编审核

### 审核流程（本地审核 → GitCode PR 操作）

#### 1. 查看待审 PR

在 GitCode 平台上查看待审 Pull Request 列表，确认新提交的 PR。

#### 2. 本地审核

```bash
# 拉取远程分支
git fetch origin

# 检出 PR 分支进行本地检查
git checkout feat/<软件名>-<版本>

# 检查变更内容
git diff main...HEAD --stat          # 变更文件概览
git diff main...HEAD -- archives/    # 归档文件差异

# 使用 review 命令辅助检查（执行 12 项自检 + 额外审核）
./scripts/ohc-run.py review --check <软件名> <版本>
```

#### 3. 通过 → 接受 PR

在 GitCode 平台上接受 PR（选择 **Squash 合并**）：

- 合并方式：Squash and Merge（保持 main 分支历史整洁）
- 合并后本地同步：

```bash
git checkout main
git pull origin main
```

#### 4. 拒绝 → 拒绝 PR

在 GitCode 平台上拒绝 PR，附评论说明原因：

- 注明具体问题（如：补丁缺失、manifest 字段不完整、构建残留未清理等）
- 协作者修复后重新推送分支并创建新 PR

#### 5. 合并后自动操作

PR 合并到 main 后，主编在本地执行以下操作：

```
① draft/ 草稿 → knowledge/graph/ 正式目录
② 重建 knowledge/graph/index.tsv
③ 重建 archives/_index.yaml
④ 重建 SUMMARY.md
⑤ 收割版本级 skill-feedback → 根级
⑥ 提交索引更新到 main 分支
⑦ 输出操作摘要
```

---

## 归档目录结构

### 文件命名统一

| 用途 | 正确名称 | 禁止名称 |
|------|---------|----------|
| 测试报告 | `test-report.md` | `TEST_REPORT.md` `build-report.md` |
| 质量报告 | `quality-report.md` | （ohc-run.py verify-build 固定输出） |
| SKILL 反馈 | `skill-feedback.md` | `feedback.md` |
| 进展记录 | `PROGRESS.md` | `progress.md` `STATUS.md` |
| 安装脚本 | `install.sh` | `{name}-install.sh` |
| 发布说明 | `RELEASENOTE.md` | `CHANGES.md` `HISTORY.md` |

### 一致性检查项

| 检查项 | 方法 | 允许差异 |
|--------|------|---------|
| 状态一致性 | grep status: manifest vs PROGRESS | 不允许 |
| 补丁数量 | manifest patches_applied vs 磁盘 *.patch 数 | 不允许 |
| 对话记录 | PROGRESS.md 中对话出现次数 | 至少 1 轮 |

---

## 补丁规范

### 命名格式

```
NNNN-{文件名}.patch
```

- **NNNN**: 四位数字序号（0001 开始，连续编号）
- **{文件名}**: 小写字母 + 连字符

### 示例

```
patches/
├── 0001-config.guess.patch      # config.guess HarmonyOS 检测
├── 0002-config.sub.patch        # config.sub ohos 三元组
└── 0003-fix-include-path.patch  # 头文件路径修复
```

### 要求

1. **格式**: unified diff（`diff -u` 或 `git diff`）
2. **上下文**: 至少 3 行
3. **单一职责**: 每个补丁解决一个问题
4. **可复现**: 原始 tarball + 补丁集 → 100% 重现相同产物
5. **可验证**: `patch --dry-run -p1` 干净通过
6. **可上游**: 有 `#ifdef __OHOS__` 守卫，可提交给上游

### 禁止

- sed 直接改 configure/Makefile 等生成文件（不可复现）
- 修改层级优先级：① configure.ac/CMakeLists.txt/源码 > ② .in 文件 > ③ Makefile > ④ ❌ 禁止改二进制

---

## 预编译包制作

详见 [knowledge/operations/packaging.md](knowledge/operations/packaging.md) v2.3。

### 核心要求

1. **tar.gz 内部必须为扁平结构**：bin/ share/ lib/ 在顶层，禁止嵌套
2. **打包命令**：`cd $PKGDIR && tar czf output.tar.gz *`
3. **debug 包必须打包**
4. **ELF 签名**：binary-sign-tool adhoc self-sign
5. **权限修复**：签名后必须 chmod +x（签名工具会重置权限）

### 9 步流程概要

```
Step 1:  make install 到独立目录
Step 2:  清理缓存和非必要文件
Step 3:  符号链接替换（wrapper/cp）
Step 4:  收集外部依赖库到 lib/external/
Step 5:  设置 RPATH（$ORIGIN 相对路径）
Step 6:  Strip debug 符号 + 分离保存
Step 7:  ELF 签名（adhoc self-sign）
Step 8:  统一修复执行权限（必做！）
Step 9:  (已简化，使用统一通用 install.sh)
Step 10: 打包 tar.gz（扁平结构）
```

---

## install.sh 规范

每个软件的 install.sh 基于 [scripts/ohc-run.py install-template (已归档)](scripts/ohc-run.py install-template (已归档)) 生成。

### 核心原则

| 原则 | 说明 |
|------|------|
| 极简依赖 | 只用 POSIX sh + tar + curl + cp + chmod |
| 纯 ASCII | 禁止 emoji/颜色码/多字节字符 |
| 扁平释放 | bin/lib/share 直接落到 ~/usr/local/ |
| 管道安全 | 禁止 heredoc（与 \| sh 冲突） |
| 参数化 | `sh -s -- {version}` 接受版本参数 |

### 目录约定

```
~/usr/local/           # 公共根（所有软件共享）
├── bin/               # 所有命令汇聚
├── lib/
│   ├── pkgconfig/     # .pc 文件池
│   └── external/      # 外部依赖库
└── share/
    └── man/man1/
```

### 禁止事项

| 禁止项 | 原因 |
|--------|------|
| set -e | cp 遇保护文件报错中断后续步骤 |
| heredoc (<< EOF) | 与 \| sh stdin 冲突 |
| emoji / Unicode | toybox ash 截断多字节 |
| --strip-components | toybox tar 不支持 |
| source / . | 非 POSIX 标准 |
| [[ ]] | bashism |

---

## manifest.yaml 必填字段

### 核心字段

```yaml
software: example              # 软件名称（小写）
version: 1.0.0                 # 版本号
status: success               # success | partial | failed
build_system: autotools        # autotools | cmake | meson | makefile | custom-perl
compile_date: 2026-04-08      # YYYY-MM-DD
```

### 推荐字段

```yaml
dependencies:
  required: []                 # 必需依赖
  optional: []                 # 可选依赖

build_config:
  target: aarch64-unknown-linux-ohos
  options: []                  # 额外 configure 参数（尽量为空！）

patches_applied:              # ohc-run.py refresh-patch 自动填充
  - file: 0001-xxx.patch
    purpose: HarmonyOS 平台检测

patch_generation:             # ohc-run.py refresh-patch 自动填充
  method: auto
  source_hash: sha256:...
  patch_hash: sha256:...

build_cleanliness:            # P0 参数最少化原则
  standard_params_only: true
  extra_params: []             # 技术债务列表

compatibility:
  level: high                  # high | medium | low
  issues: []
  notes: ""

test_results:
  type: official               # official | manual | skipped
  total: N
  passed: N
  failed: N
  note: ""

knowledge_gained: []          # 本次沉淀的 L3 笔记
skill_feedback: []             # 流程自省反馈
knowledge_ref: []             # 引用的 E 编号列表（主编审核用）
```

---

## 知识库更新

### 写入时机

每次编译过程中遇到新问题时，判断是否通用：

```
问题 → "下一个不同软件也会遇到吗？"
  ├─ 是 → L1（平台真理）或 L2（类别模式）→ graph add --draft → 草稿
  └─ 否 → L3（版本笔记）→ 写入 manifest.yaml knowledge_gained
```

### 知识图谱新增条目

```bash
# 协作者：添加草稿
./scripts/ohc-run.py graph add --draft \
  --title "E082: 描述" \
  --error-pattern "错误特征" \
  --solution "解决方案" \
  --match-keywords "关键词1,关键词2"
```

主编 approve 时自动移入正式目录并重建索引。

### 更新 PREBUILD_TODOLIST.md

每完成一个软件的编译和打包后：
1. 状态改为 "✅ 完成"
2. 填写包路径和大小
3. 记录补丁数和备注
4. 更新顶部统计

---

## 辅助脚本一览

| 脚本 | 用途 | 角色 |
|------|------|------|
| `ohc-run.py init-build` | 编译初始化（含依赖检查） | 协作者 |
| `ohc-run.py build` | 13 步编译驱动 | 协作者 |
| `ohc-run.py finish` | 收尾管线（4步） | 协作者 |
| `ohc-run.py resolve-deps` | 依赖预编译包查询/安装 | 协作者 |
| `ohc-run.py refresh-patch --auto` | 补丁自动生成 | 协作者 |
| `ohc-run.py verify-build` | 质量门禁 G1-G4 | 协作者 |
| `ohc-run.py finalize-archive` | 归档收口（5阶段） | 协作者 |
| `ohc-run.py submit --check` | 提交自检（本地验证） | 协作者 |
| `ohc-run.py graph add --draft` | 添加知识草稿 | 协作者 |
| `ohc-run.py review --check` | 辅助审核检查 | 主编 |
| `ohc-run.py summary` | 生成 SUMMARY.md | 主编 |
| `ohc-run.py search-url` | URL 搜索 | 协作者 |
| `ohc-run.py check-env` | 环境变量检查 | 协作者 |

---

*最后更新: 2026-04-13 | 对齐 SKILL.md v7.2*
�索 | 协作者 |
| `ohc-run.py check-env` | 环境变量检查 | 协作者 |

---

*最后更新: 2026-04-13 | 对齐 SKILL.md v7.2*
