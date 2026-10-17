# E431 — GNU make 命令行赋值会击穿 ?= 推导 + := 重写的版本横幅逻辑

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
Makefile 版本前缀重写被命令行赋值击穿（得到 master1.1.0 而非 1.1.0）
```

实际遇到的报错：

```text
make release BRANCH=master TAG=1.1.0 -> version.h: #define VERSION "master1.1.0"
```

## 触发条件

- 分类：`build-system`
- 阶段：`configuration`
- 工具：`make`
- 适用范围：源码树中没有 .git（conan source_folder、官方发布 tarball、git archive）且 Makefile 用 ?= 从 git 推导版本号的项目

## 根因分析

GNU make 赋值优先级为 命令行 > makefile 赋值（含 := 与 ?=）> 环境变量 > 内置默认。典型 Makefile 用 ?= 从 git 推导版本再用 := 清空前缀（ifeq ($(BRANCH),master) BRANCH:=）。无 .git 时 git describe/rev-parse 失败，必须注入该值；若注入到命令行，优先级最高会使 BRANCH:= 失效、分支前缀不被清掉，横幅多出前缀。

## 解决方案

### 推荐方案

把 ?= 变量经【环境】注入而非命令行——环境变量只是默认值，不干扰 Makefile 内部的 := 重写，分支前缀逻辑照常生效。conan 侧用 GnuToolchain(self).extra_env.define()。

**方案说明**：用环境变量（extra_env）注入 git 推导型 Makefile 的 ?= 变量，让 Makefile 自身的前缀重写继续生效。

```bash
tc = GnuToolchain(self)
tc.extra_env.define("BRANCH", "master")
tc.extra_env.define("TAG", self.version)
tc.generate()
self.run('make release CC="<cc>" -j1', cwd=self.source_folder)
```

### 禁止做法

- ❌ 不要写成 make release BRANCH=master TAG=...——命令行优先级最高，会让 Makefile 的 BRANCH:= 重写失效。
  - 原因：命令行赋值在 make 中不可被 makefile 内的 := 覆盖（需 override 指令）。
  - 后果：版本横幅/嵌入的版本字符串错误（如 master1.1.0），与上游发布物不一致，且版本断言类测试会失败。

### 回退方案

若 Makefile 逻辑无法通过环境变量驱动，可改为在 build() 里用 Python 直接生成 Makefile 需要的构建期元文件（如 build/version.h），再调用 make。

## 验证

```bash
环境注入得 version.h 的 VERSION="1.1.0"（与 tag 版 master 检出一致）；命令行注入得 "master1.1.0"。由 rtl-wmbus/1.1.0 实测对照。
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 完整踩坑记录：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 7 节
