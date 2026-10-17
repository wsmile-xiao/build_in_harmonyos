# libXext / libxext 6.4.0 前置适配笔记

## 边界

- 本任务只处理 `libxext/6.4.0`。
- 文件落点采用小写包名目录：`archives/l/libxext/6.4.0/`。
- Conan 包名使用历史消费者引用的小写形式：`libxext`。
- 未修改 `libx11`、`libxscrnsaver` 或基础设施目录。
- issue 未在项目文件或源会话上下文中找到明确编号，暂记为 `TBD`。

## 版本与包名策略

历史消费者 `xclip/0.13`、`xidle/20200802` 均记录依赖
`libxext/6.4.0`。旧的 `libXext/1.3.6` 编译笔记同时记录产物
`libXext.so.6.4.0`，因此本次沿用 Conan 依赖版本
`libxext/6.4.0`，源码选择对应 upstream release `libXext 1.3.6`。

`libXext/1.7.0` 旧记录使用 `master` archive 且 sha256 为空，不适合作为
可复现 Conan 配方输入。

## W0 依赖检查

已执行：

```powershell
conan list 'libx11/6.4.0#*' -r=ohpcd
conan list 'libxext/6.4.0#*' -r=ohpcd
conan list 'xorgproto/2025.1#*' -r=ohpcd
conan list 'xorgproto/2024.1#*' -r=ohpcd
```

结果：

- `libx11/6.4.0`: found，recipe revision
  `63e25e48c3af73db324ce61d0dba9cce`，OHOS armv8 binary 可下载。
- `libxext/6.4.0`: `not found`（本任务正在补此 recipe）
- `xorgproto/2025.1`: found
- `xorgproto/2024.1`: `not found`

结论：`libx11/6.4.0` 发布后，`libxext/6.4.0` 的依赖层已闭合。
完整构建与 test_package 仍需在 OHOS 真机或单包 CI 中执行。

## 源码与构建系统分析

源码：

```text
https://xorg.freedesktop.org/releases/individual/lib/libXext-1.3.6.tar.xz
sha256: edb59fa23994e405fdc5b400afdf5820ae6160b94f35e3dc3da4457a16e89753
```

构建系统：

- upstream release tarball 自带 `configure`、`Makefile.in`、`ltmain.sh`。
- 无 `meson.build`。
- `configure.ac` 使用 `PKG_CHECK_MODULES(XEXT, [xproto >= 7.0.13] [x11 >= 1.6] [xextproto >= 7.1.99])`。
- 默认非 OpenBSD/Solaris 平台 `XEXT_SOREV=6:4:0`，即产物
  `libXext.so.6.4.0`。
- `src/Makefile.am` 构建 `libXext.la`，源码包括 `DPMS.c`、`XShape.c`、
  `XShm.c`、`XSync.c`、`extutil.c` 等。
- 源码中未发现 `check_PROGRAMS` 或 `TESTS`；上游没有实质测试套件。

配方策略：

- 使用 `AutotoolsToolchain` + `Autotools`。
- 禁用文档/specs 生成：`--disable-docs`、`--disable-specs`、
  `--without-xmlto`、`--without-fop`、`--without-xsltproc`。
- 依赖 `xorgproto/2025.1` 以提供 `xproto`、`xextproto` pkg-config 模块。
- 依赖 `libx11/6.4.0`，并将其 pkg-config 模块名映射为 `x11`。
- test_package 调用本地 API，不需要 X server。

## 本机轻量验证

已完成：

- `conan inspect .` 通过。
- Python AST 语法检查通过：`conanfile.py`、`test_package/conanfile.py`。
- YAML 解析通过：`conandata.yml`、`manifest.yaml`、
  `test_package/MANIFEST.yml`。
- `conan source .` 已在临时目录
  `D:/harmonyos/tmp/libxext-conan-source-check` 通过，归档目录未被源码解包污染。
- official tarball 下载并校验 sha256。
- 源码结构检查：Autotools-only release tarball。
- W0 依赖检查：确认 `libx11/6.4.0` 已在 ohpcd 发布并能下载
  OHOS armv8 binary。
- `conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default`
  在 Windows 本机失败于 `xcb-proto/1.17.0` build context 校验：

```text
ERROR: xcb-proto/1.17.0: Invalid configuration: xcb-proto supports Linux and OHOS, not Windows
```

  这是本机 Windows build profile 限制，不是 `libxext` 源码或 recipe
  依赖缺失。
- `conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
  通过，依赖图包含 `libx11/6.4.0`、`libxcb/1.16`、
  `xtrans/1.6.0`、`xorgproto/2025.1`、`libxau/1.0.11`、
  `libxdmcp/1.1.5`。
- `conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never -of D:/harmonyos/tmp/libxext-install-check`
  通过，生成器阶段成功，并从 ohpcd 下载了 `libx11/6.4.0`
  package revision `0e5934cee0577987a9f173673f0cb4a2`。
- `conan install archives/l/libxext/6.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never -of D:/harmonyos/tmp/libxext-install-check2`
  通过，用于确认 OHOS 工具路径与 `XEXT_CFLAGS/XEXT_LIBS` 兜底后的
  `generate()` 阶段正常。

## OHOS 单包 CI 验证

已使用用户指定真机：

```powershell
ssh -T -p 33332 -i "$env:USERPROFILE\.ssh\ohos_pc_codex_ed25519" currentUser@frp-tip.com
```

远端同步目录：

```text
/storage/Users/currentUser/validation/build_in_harmonyos/archives/l/libxext/6.4.0
```

最终通过命令：

```sh
CI_PACKAGES="archives/l/libxext/6.4.0" zsh ci/conan/build_and_test.sh
```

最终日志：

```text
/storage/Users/currentUser/libxext-6.4.0-ci-20260809-140503.log
```

结果：

- L0 通过；`libx11/6.4.0`、`xorgproto/2025.1` 均可从 ohpcd/cache 解析。
- `libxext/6.4.0#1e36648863141b2f0ac04b0e012ed69e:e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab`
  构建并打包成功，产物包含 `libXext.so.6.4.0`。
- `test_package` 通过 CMake 构建并运行，输出：

```text
libxext api smoke ok
```

2026-08-10 路径小写化后复跑：

- `CI_PACKAGES="archives/l/libxext/6.4.0" zsh ci/conan/build_and_test.sh`
  通过。
- CI 外层识别为 `Building: libxext/6.4.0`，Conan 导出 ref 为
  `libxext/6.4.0`。
- `test_package` 输出 `libxext api smoke ok`。
- `Build Summary`: Total 1, Success 1, Failed 0。

过程中修复/确认的 OHOS 环境点：

- 远端非交互环境没有 `/data/service/hnp/bin/bash` 与
  `/data/service/hnp/bin/clang`，实际工具位于 `$HOME/usr/local/bin`；
  配方和 test_package 均在本包内回落到可执行的 shell/clang/LLVM 工具。
- 远端无 `pkg-config`，配方通过 Conan 依赖目录生成
  `XEXT_CFLAGS` 与 `XEXT_LIBS`，覆盖 `xproto`、`x11`、`xextproto` 以及
  Conan 分包下需要的 `libxau` 头目录。
- 上游 `configure` 不识别 `--disable-docs`，只警告不阻断；
  `--disable-specs` 生效，man page 仍由源码内规则生成。
- 成功日志中仍保留早期运行时的分支名大小写警告：
  `feat/libxext-6.4.0` 不包含 `libXext-6.4.0`。后续采用小写目录
  `archives/l/libxext/6.4.0/` 后，分支名与包目录保持一致。

下一步：

- 提交/推送分支后走 PR 流水线与 REL upload 复核。
