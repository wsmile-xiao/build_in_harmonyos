# DRAFT — GitHub tag tarball 不含 autotools 生成文件，配方需 autoreconf 自举 + tool_requires

> 配对 .kv：`DRAFT-irstlm-6.00.05-git-tag-no-configure-autoreconf-bootstrap.kv`
> 来源：irstlm 6.00.05（2026-09-21 适配，任务 irstlm-6.00.05-r01-pc1-56）

## 问题

irstlm 6.00.05 只有 GitHub tag 分发（`archive/refs/tags/v6.00.05.tar.gz`）。
`conan create` 的 build() 直接 `autotools.configure()` 报：

```
/system/bin/sh: .../configure: inaccessible or not found
irstlm/6.00.05@ohpcd/stable: Error in build() method, line 54
    autotools.configure()
    ConanException: Error 127 while executing
```

解压 tarball 后确认：仓库只有 `configure.ac`、`Makefile.am`、`regenerate-makefiles.sh`，
**没有** `configure`、`config.guess`、`config.sub`、`Makefile.in`、`install-sh`。

## 根因

autotools 的生成文件（configure / config.guess / config.sub / 各层 Makefile.in /
install-sh / depcomp / ltmain.sh）由 autoreconf/automake/autoconf/libtoolize 在发布时
生成，上游 git 仓库只跟踪输入文件（configure.ac、Makefile.am、m4 宏）。GitHub 的
git-archive 快照（tag/release 源码 zip/tar.gz）只打包 git 跟踪的文件，因此不含
configure。这与上游发布流程中 `make dist` 生成的 **release tarball**（含全部生成物）
不同——判别法是解压后看是否存在 `configure` 文件。

## 修复（irstlm 6.00.05 验证通过）

1. `build_requirements()` 提供自举工具（CI 沙箱缺 aclocal/automake/libtoolize）：
   ```python
   def build_requirements(self):
       self.tool_requires("automake/1.18")
       self.tool_requires("libtool/2.5.4")
   ```
   tool_requires 用 **build profile** 解析，`conan create` 必须同时传 `-pr:h` 与 `-pr:b`
   （本项目 conan-verify 已如此调用）。

2. `build()` 在 source_folder 先自举再 configure：
   ```python
   def build(self):
       self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
       autotools = Autotools(self)
       autotools.configure()
   ```
   irstlm 自带 `regenerate-makefiles.sh`（autoreconf + libtoolize --force +
   automake --add-missing 兜底），等价可 `sh regenerate-makefiles.sh`。

## 验证

- `conan create`（ohos-aarch64, build=missing）全绿，test_package 1/1 Passed；
- finish W3 本地 CI：L0(L1/L2/L4/L5 全 pass, Pass rate 100%)，.ci-result.json 写入。

## 适用条件

- 源码分发为 GitHub/GitLab git-archive（含 tag archive），**解压后无 configure**；
- 反例：release tarball（make dist 产物）自带 configure/Makefile.in/ltmain.sh，
  免自举、免 automake/libtool tool_requires（见 DRAFT-5982-gmime）。

## 边界 / 限制

- autoreconf 需要 aclocal/autoconf/autoheader/automake/libtoolize 在 PATH；
  CI 沙箱只带 autoconf 套件，必须 tool_requires 补齐 automake+libtool；
- 自举还可能暴露缺 m4 宏（gtk-doc.m4 等）或 automake 输入文件缺失问题，按
  E041/E089 处理；
- 生成文件不入 git 提交（R39）。

## 恢复条件 / 后续

自举成功后会进入正常 configure 流程；后续若遇 HMDFS config.status 临时目录
权限问题（`subs1.awk Permission denied`），见 E011/E052/E060/E110/E112/E175
（umask 077 修复），两者是前后置关系。

## 验证命令（可复现）

```bash
tar -tzf irstlm-6.00.05.tar.gz | grep -c '/configure$'      # 0 → 需自举
tar -tzf irstlm-6.00.05.tar.gz | grep -c '/Makefile.in$'    # 0 → 需自举
```
