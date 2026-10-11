# DRAFT-12283 — 发布源码归档的版本来源不可依赖 git

## 错误特征

```text
# 现象一：发布 tarball 构建后版本为空
$ ydotool/ydotoold --version
unknown                       # 源码 #ifndef VERSION 分支

# 现象二（更隐蔽）：构建目录位于无关 git 仓库内时注入无关标签
$ ./ydotoold --version
webp-pixbuf-loader-0.2.7-src-4871-gb01a5b784     # 另一个项目的标签！

# 现象三：可选文档工具缺失直接构建失败
$ make
/bin/sh: scdoc: command not found                # Makefile ALL target 无条件执行 scdoc
```

## 触发条件

- 构建系统: CMake（本实例；其他构建系统同理）
- 阶段: configuration（版本宏生成）/ packaging（版本报告）
- 场景: 上游用 `execute_process(git describe …)` 生成版本宏并以发布 tarball 分发；
  或把文档工具（scdoc 等）作为无条件构建目标
- 环境: 发布 tarball 无 `.git`；或构建目录恰好位于任意（无关）git 仓库内

## 根因分析

1. GitHub/GitLab 的 tag tarball **不含 git 元数据**，`git describe` 必然失败；
   上游只在成功分支定义 `VERSION`，失败的后果是空值/`unknown`。
2. `git describe` 的行为取决于**当前工作目录的祖先目录里最近的 `.git`**：
   在“构建目录恰处于无关仓库内”的场景（本包在 worktree 下手工构建时实测命中，
   观测记录见归档 `archives/y/ydotool/1.0.4/notes.md` 验证结果段），
   它会成功并返回**无关标签**，比“失败”更危险——版本号看起来正常但完全错误。
3. 因此“版本来源”的正确优先级应为：**打包注入 > git 元数据（开发态）> 发布兜底**；
   任何“只看 git”的实现都会在发布归档路径上出错。
4. 同源工程性问题：把**可选文档工具**（scdoc）当作无条件 ALL target，会把
   “文档生成”变成构建硬依赖；`cmake_minimum_required(VERSION 3.4)` 在
   CMake ≥4.0 亦被拒绝（<3.5 兼容移除，E103/E187）。

## 解决方案（推荐）

1. **版本三级回退（小补丁）**：
   ```cmake
   if (DEFINED YDOTOOL_VERSION)          # 打包注入（配方从 self.version 传入）
       set(GIT_VERSION "${YDOTOOL_VERSION}")
   else()
       execute_process(COMMAND git describe --tags --long --always
                       RESULT_VARIABLE RC_GIT_VER OUTPUT_VARIABLE GIT_VERSION)
       if (NOT RC_GIT_VER STREQUAL "0")
           set(GIT_VERSION "1.0.4")      # 发布兜底
       endif()
   endif()
   string(STRIP "${GIT_VERSION}" GIT_VERSION)
   add_definitions(-DVERSION=\"${GIT_VERSION}\")
   ```
2. **配方侧注入**：`tc.variables["YDOTOOL_VERSION"] = self.version`（Conan
   CMakeToolchain），保证包版本稳定且可复现；补丁保留覆盖入口而不是写死。
3. **可选工具门控**：`find_program(SCDOC_EXECUTABLE scdoc)`，缺失时跳过 man 页。
4. **CMake policy**：配方注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（零补丁，
   与上游后续版本修法一致，ref E103/E187）。

## 禁止做法

- 不要在补丁里写死版本而没有可覆盖入口（换版本目录即失效且易被忽视）。
- 不要依赖构建环境的 git 状态生成版本号（CI/打包环境不可控）。
- 不要为了“版本好看”把 `unknown` 静默替换成别的字符串而不留回退逻辑。

## 验证

```bash
# 覆盖优先（在任意 git 仓库目录内运行也应得到 1.0.4）
cmake -S src -B build -DYDOTOOL_VERSION=1.0.4 && cmake --build build
./build/ydotoold --version            # -> 1.0.4
# 无覆盖 + 非仓库目录 -> 发布兜底
cd /tmp && cmake -S <src> -B <build2> && cmake --build <build2>
<build2>/ydotoold --version           # -> 1.0.4
# 反例证据（无覆盖 + 无关仓库目录）曾输出 webp-pixbuf-loader-… 标签
# （观测记录见 archives/y/ydotool/1.0.4/notes.md 验证结果段）
```

## 查重差异（与已有知识库）

- `E103`/`E187`（CMake policy 版本兼容）：讲 `cmake_minimum_required` 门槛，
  本条讲**版本宏的数据来源优先级**（git 不可依赖），二者为不同问题，policy
  部分引用 E103/E187。
- `git describe` / `VERSION 宏` / `版本注入` 在正式索引（540 条）中 0 命中；
  既有草稿中亦无“发布归档版本来源”主题。
- `DRAFT-12283-ohos-uinput-…` / `…-socket-dependent-tests-probe-gated-adaptation`
  讲平台权限边界；本条是**构建可复现性**问题，与平台无关（在任意 Linux 上同样成立）。

## 关联条目

- similar_to: E103、E187（CMake policy 兼容）
