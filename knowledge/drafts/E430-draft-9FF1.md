# E430 — SCons 工程语言预检误判：识别表无 SCons 信号 + 子树稀释主体统计

## 错误特征

`lang-preflight`（scripts/ohc/lang_detect.py）在 SCons 工程上给出错误判定，典型输出：

```
detected_language: java
language_evidence: manifest: (none) / build system: Makefile|gradle / source stats: ...
```

即一个主体为 C++ 的库被判成 `java`（或 `mixed`），随后任务按 R47 被写成
`env_unsupported` 终态——明明是可适配的 SCons C++ 库，却被语言闸拦下。

## 触发条件

- 构建系统: SCons（`SConstruct`/`SConscript`）——识别表里没有对应条目
- 源码树同时带非目标平台子树：`android/`（含 `*.java`、`build.gradle`）、`ios/`、`darwin/` 等
- 阶段: 语言预检（R47，checkout 后、适配主流程之前）

## 根因分析

语言预检的判定优先级是 **manifest > 构建系统 > 源码统计（≥70%）**。SCons 工程踩两个坑：

1. **构建系统识别表未覆盖 SCons**：表里只有 Cargo/pyproject/go.mod/CMakeLists.txt/Meson/
   QMake 等，`SConstruct`/`SConscript` 命中不了 → 直接退化到"源码统计"一级。
2. **全树统计被子树稀释**：工程常把 Android 壳（`android/` + `*.java` + Gradle）放在同一
   tarball 里，全树统计的 java 占比被抬高，主体 C++（`src/`）占比掉到 70% 阈值以下 →
   判 `java`/`mixed`。

实测（rhvoice 1.14.0）：全树统计判 `java`；用 tar 排除法只保留桌面作用域树后，
`detected=cpp`，主体占比 85%（R47 边界规则：主体语言按主体判，非目标平台子树不计）。

## 解决方案

### 推荐方案

按 R47 主体口径重建"作用域树"，再对作用域树跑预检：

```bash
# 1. 只解出目标平台作用域（排除 android/ios/java 等非目标子树）
tar xf <src>.tar.gz -C <dir> \
    --exclude="*/android/*" --exclude="*/ios/*" --exclude="*/java/*"

# 2. 对作用域树做语言预检（主体统计 ≥70% 即按主体语言判）
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight <name> <ver> --src <dir>
```

配套：`sh knowledge/scons-detect.sh <src>` 会同时输出 `*.java` 文件数与
`android/`、`ios/`、`darwin/` 子树是否存在，用来判断是否需要重建作用域树。

被判定为 C++ 后，任务记 `lang_checked` 草稿继续主流程（c↔cpp 属兼容族，不迁移）。

### 禁止做法

- ❌ 对含 `android/` 子树的全树直接判语言：主体被稀释，会把可适配的 C++ 库误判为
  `java`/`mixed`，任务被错误写成 `env_unsupported` 终态。
- ❌ 用 `cp -al <src>` 复制出作用域树：HMDFS（FUSE）上硬链接创建失败，拷贝会变成空树或
  直接报错，预检仍跑在全树上，误判复发。
- ❌ 在未核验主体语言的情况下靠 `--lang` 硬覆盖：覆盖只在清点过主体（构建系统 + 主体统计）
  后用于消除边界歧义，不能用来绕过预检。

## 验证

```bash
# 主体作用域重建后应得 detected=cpp（样例 rhvoice 1.14.0：主体 85%）
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight rhvoice 1.14.0 --src <scope-tree>

# 辅助：确认子树才是罪魁
sh knowledge/scons-detect.sh <src> | grep -E "java files|subtree present"
```

## 关联条目

- 相关: E429（SCons 交叉编译构造变量注入——同一类工程的构建坑）
- 样例库: `archives/r/rhvoice/1.14.0/`
- 规则: R47（语言预检前置，缺字段 = PROTOCOL_VIOLATION）；不匹配的合法终态为
  `env_unsupported` + `detected_language` + `language_evidence` 三项
