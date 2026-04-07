# 贡献指南

> 如何为鸿蒙编译知识库添加新软件或改进现有内容。

## 目录

- [添加新软件](#添加新软件)
- [归档目录结构](#归档目录结构)
- [补丁规范](#补丁规范)
- [预编译包制作](#预编译包制作)
- [install.sh 规范](#installsh-规范)
- [manifest.yaml 字段](#manifestyaml-必填字段)
- [知识库更新](#知识库更新)

---

## 添加新软件

### 方式 A：使用 SKILL 五步走流程（推荐）

SKILL.md v4.0 定义了标准五步走流程：

```
Step 1:  init-build.sh          初始化（下载/解压/骨架）
Step 2:  AI 编译                 configure + make + make install
Step 2.5: 独立目录安装验证       干源码 + 补丁 + 独立 TEST_PREFIX
Step 3:  make check / 功能验证   测试套件或手动功能测试
Step 4:  verify-build.sh         质量门禁（G1-G4 四道检测）
Step 5:  预编译包制作            10 步打包流程
Step 5.5: finalize-archive.sh    归档收口
```

一键启动：

```bash
./scripts/init-build.sh <软件名> <版本> [--url=<下载URL>]
# 然后 AI 执行 Step 2 ~ Step 5.5
./scripts/finish-build.sh <软件名> <版本> success
```

### 方式 B：手动创建档案

如果不用 init-build.sh，手动按以下步骤：

#### 1. 创建目录结构

```bash
mkdir -p archives/{首字母}/{软件名}/{版本}/{patches,reports,packaging}
```

**双层结构**（v4.0 强制）：

```
archives/{首字母}/{软件名}/          ← 软件级（跨版本共享）
├── README.md                        # 编译说明
├── RELEASENOTE.md                   # 发布说明（多版本聚合，自动生成）
├── install.sh                       # 安装脚本（参数化: sh -s -- <ver>）
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
# 使用 refresh-patch.sh 自动生成（推荐）
./scripts/refresh-patch.sh --auto <软件名> <版本>

# 或手动生成
diff -Naur original/ modified/ > patches/0001-description.patch
```

#### 4. 验证

```bash
# 质量门禁
./scripts/verify-build.sh <软件名> <版本>

# 归档收口（自动清理+校验+生成 RELEASENOTE）
./scripts/finalize-archive.sh <软件名> <版本>
```

---

## 归档目录结构

### 文件命名统一

| 用途 | 正确名称 | 禁止名称 |
|------|---------|----------|
| 测试报告 | `test-report.md` | `TEST_REPORT.md` `build-report.md` |
| 质量报告 | `quality-report.md` | （verify-build.sh 固定输出） |
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

详见 [knowledge/packaging.md](knowledge/packaging.md) v2.3。

### 核心要求

1. **tar.gz 内部必须为扁平结构**：bin/ share/ lib/ 在顶层，禁止嵌套
2. **打包命令**：`cd $PKGDIR && tar czf output.tar.gz *`
3. **debug 包必须打包**
4. **ELF 签名**：binary-sign-tool adhoc self-sign
5. **权限修复**：签名后必须 chmod +x（签名工具会重置权限）

### 10 步流程概要

```
Step 1:  make install 到独立目录
Step 2:  清理缓存和非必要文件
Step 3:  符号链接替换（wrapper/cp）
Step 4:  收集外部依赖库到 lib/external/
Step 5:  设置 RPATH（$ORIGIN 相对路径）
Step 6:  Strip debug 符号 + 分离保存
Step 7:  ELF 签名（adhoc self-sign）
Step 8:  统一修复执行权限（必做！）
Step 9:  创建 install.sh（单独托管，不打包进 tar.gz）
Step 10: 打包 tar.gz（扁平结构）
```

---

## install.sh 规范

每个软件的 install.sh 基于 [scripts/install-template.sh](scripts/install-template.sh) 生成。

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

patches_applied:              # refresh-patch.sh 自动填充
  - file: 0001-xxx.patch
    purpose: HarmonyOS 平台检测

patch_generation:             # refresh-patch.sh 自动填充
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
```

---

## 知识库更新

### 写入时机

每次 Phase 3 编译过程中遇到新问题时，判断是否通用：

```
问题 → "下一个不同软件也会遇到吗？"
  ├─ 是 → L1（平台真理）或 L2（类别模式）→ 写入 knowledge/
  └─ 否 → L3（版本笔记）→ 写入 manifest.yaml knowledge_gained
```

### error-patterns.md 新增条目

格式：`E{NNN}: {简短描述}`

```markdown
### E068: 示例错误描述
- 类别: 编译/链接/运行时/打包
- 现象: 错误信息特征
- 根因: 为什么发生
- 解决方案: 具体操作步骤
- 影响: 哪些软件可能遇到
```

### 更新 PREBUILD_TODOLIST.md

每完成一个软件的编译和打包后：
1. 状态改为 "✅ 完成"
2. 填写包路径和大小
3. 记录补丁数和备注
4. 更新顶部统计

---

## 辅助脚本一览

| 脚本 | 用途 | 调用方式 |
|------|------|----------|
| `init-build.sh` | 编译初始化 | Step 1 入口 |
| `finish-build.sh` | 收尾管线（4步） | Step 3 结束后 |
| `refresh-patch.sh --auto` | 补丁自动生成 | finish 内部 |
| `verify-build.sh` | 质量门禁 G1-G4 | Step 4 必须 |
| `finalize-archive.sh` | 归档收口（5阶段） | Step 5.5 必须 |
| `init-archive.sh` | 档案骨架创建 | init 内部 |
| `install-template.sh` | install.sh 模板 | 打包时参考 |
| `detect-build-system.sh` | 构建系统检测 | 可选 |
| `search-download-url.sh` | URL 搜索 | init fallback |
| `check-env.sh` | 环境变量检查 | init 内部 |

---

*最后更新: 2026-04-08 | 对齐 SKILL.md v4.0*
