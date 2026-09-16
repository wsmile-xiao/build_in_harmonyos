# E569 — conan basic_layout() 的 build_folder 落在 source_folder 之内，构建期 copytree 复制源码到 build 目录会自递归卡死

## 错误特征

conan `build()` 里把源码复制进构建目录后再操作，出现**无限递归/卡死**：

```
RecursionError / OSError [Errno 36] File name too long
# 或：进程 CPU 100% 长时间无输出，build-release/build-release/... 层层嵌套
```

## 触发条件

- 构建系统：conan 2.x，配方使用 `conan.tools.layout.basic_layout(self)`
- 阶段：testing（或任何在 build 目录搞「布局准备」的步骤）
- 触发源：`shutil.copytree(source_folder, build_folder/...)` 之类把源码复制进构建目录的逻辑

## 根因分析

`basic_layout()` 默认把 `build_folder` 设为 `<source_folder>/build-release`，即**构建目录位于源码目录之内**。若构建逻辑把整个 `source_folder`（或含 build 目录的父目录）复制到 `build_folder` 之下，复制源里已经包含复制目标自身，于是每次复制都把上一次的产物再复制一遍，无限自递归（实测 CPU 100%、卡死数分钟）。autotools/cmake 因 out-of-source 约定通常不触发，但自研 python/shell 构建逻辑很容易踩。

## 解决方案

### 推荐方案（就地运行，不复制）

直接在 `source_folder` 内就地运行，不复制源码：

```python
proc = subprocess.run(cmd, cwd=self.source_folder, env=env)   # 就地，不 copytree
```

### 回退方案

确需独立副本时，`shutil.copytree(..., ignore=shutil.ignore_patterns("build*", ...))` 显式排除 `build_folder`（及其它 conan 生成目录），避免把自身纳入复制源。

### 禁止做法

- ❌ 把整个 `source_folder` 原样 copytree 进 `build_folder`（basic_layout 下必然自递归）。
- ❌ 用 sleep/重试「等它跑完」——它是死循环，不是慢。

## 验证

```bash
cd archives/a/afl-utils/1.35a
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
# 就地运行后不再卡死，构建期正常打印 UPSTREAM-PYTEST-SUMMARY
```

## 关联条目

- 相关: E568（上游测试 /tmp + setsid 平台适配）
