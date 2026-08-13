# libxscrnsaver 1.2.5 前置适配记录

## 任务信息
- 目标库: libxscrnsaver
- 上游项目: libXScrnSaver
- 版本: 1.2.5
- Issue: 待补。本轮在项目内搜索 `libxscrnsaver` / `xscrnsaver` / `XScreenSaver`，未找到明确 issue 编号。
- 分支: `feat/libxscrnsaver-1.2.5`
- Worktree: `D:\harmonyos\worktrees\libxscrnsaver`

## W0 依赖检查
上游 Meson / Autotools 均声明依赖:
- `x11`
- `xext`
- `xextproto`
- `scrnsaverproto >= 1.2`

本轮检查结果:
- `xorgproto/2025.1`: `conan download -r=ohpcd --only-recipe` 成功，可提供 `xextproto` 和 `scrnsaverproto`。
- `xtrans/1.6.0`: `conan download -r=ohpcd --only-recipe` 成功，仅作为 X11 链路参考。
- 依赖拆分后，`libx11/6.4.0` 已可从 `ohpcd` 下载 recipe，并已有本机 OHOS binary cache。
- `libxext/6.4.0` 已发布到 `ohpcd`。2026-08-11 复查 `conan download libxext/6.4.0 -r=ohpcd --only-recipe` 成功，recipe revision 为 `20942ab436730e84acb01dcf565fda68`；`conan list "libxext/6.4.0:*" -r=ohpcd` 可见 OHOS armv8 binary `e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab`。
- 大小写包名 `libX11/*`、`libXext/*`: 远端返回 `invalid name`，Conan 包名应使用小写。

结论: 当前 libxscrnsaver 配方依赖图已闭合，且已在 OHOS 设备侧完成单包构建与 test_package。`libxext/6.4.0` 现已在 `ohpcd` 发布 recipe 和 OHOS armv8 binary。本 PR 不 vendor、不修改依赖库内容。

## 源码与构建系统分析
- 源码 URL: `https://www.x.org/releases/individual/lib/libXScrnSaver-1.2.5.tar.xz`
- sha256: `5057365f847253e0e275871441e10ff7846c8322a5d88e1e187d326de1cd8d00`
- 构建系统:
  - `meson.build`: 存在，Meson >= 1.1.0。
  - `configure.ac`: 存在，Autotools 方案依赖 `xorg-macros` 和 pkg-config。
- 本轮选择 Meson recipe，原因是上游 Meson 直接声明依赖并安装 `libXss`、`scrnsaver.h`、`xscrnsaver.pc`，比 Autotools 更少触发 `config.guess/config.sub` 与 HMDFS 临时文件问题。
- 上游没有独立测试套件；`meson.build` 只构建库、安装头文件、生成 man page。

## Conan 配方策略
- 主配方使用 `MesonToolchain` + `PkgConfigDeps` + `VirtualBuildEnv`。
- 依赖按未来 Conan 包形态声明:
  - `libx11/6.4.0`
  - `libxext/6.4.0`
  - `xorgproto/2025.1`
- `PkgConfigDeps` 显式映射 `libx11 -> x11`、`libxext -> xext`，匹配上游 `meson.build` 的 `dependency('x11')` / `dependency('xext')`。
- `default_library` 跟随 `shared` 选项，默认 `shared=True`。
- OHOS shared 构建后对真实 `.so*` 执行 `binary-sign-tool -selfSign 1`，避免安装后 `.codesign` 失效导致 dlopen/执行时报 `Permission denied`。
- 注入 `llvm-ar` / `llvm-ranlib` 到 `conan_meson_native.ini`，复用本仓库 Meson 配方常见处理。
- OHOS worker 上缺 `meson` 时，build 阶段通过当前 Python `pip install --user meson` 兜底。
- 当前 worker 的 profile 写死 `/data/service/hnp/bin/clang`，但实际工具在 `/storage/Users/currentUser/usr/local/bin`；recipe 会在 profile 路径不存在时从 PATH 回退查找 clang、clang++、llvm-ar、llvm-ranlib、llvm-objcopy 和 binary-sign-tool。
- build 阶段设置 `TMPDIR` / `TMP` / `TEMP` 到 Conan build 目录，避免 clang 在只读默认临时目录下报 `unable to make temporary file: Read-only file system`。
- worker 无系统 `pkg-config` / `pkgconf`；recipe 在 generators 目录生成最小 `pkg-config` helper，供 Meson 读取 Conan 生成的 `.pc` 文件。
- 上游 Meson 直接查 `xextproto.pc` / `scrnsaverproto.pc`，而 Conan 依赖为合并包 `xorgproto/2025.1`；generate 阶段复制并重写这两个 `.pc` 到 generators 目录。

## test_package
`test_package/test.c` 不是空壳测试:
- 包含 `<X11/extensions/scrnsaver.h>`。
- 调用 `XScreenSaverAllocInfo()`，验证 `XScreenSaverInfo` 字段可写。
- 使用 `XFree()` 释放内存，覆盖 `libXss` 与 `libX11` 链接。
- 不连接 X server，不依赖 `DISPLAY`，适合真机/CI smoke。

## 本机验证
已完成:
- 源码包下载与 sha256 校验。
- 源码结构、依赖、构建系统分析。
- `conan download xorgproto/2025.1 -r=ohpcd --only-recipe` 成功。
- `conan download xtrans/1.6.0 -r=ohpcd --only-recipe` 成功。
- `conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 进入 OHOS 图解析后失败于 `libx11/6.4.0`: `Unable to find 'libx11/6.4.0' in remotes`。
- 2026-08-10 复检:
  - `conan download libx11/6.4.0 -r=ohpcd --only-recipe` 成功，recipe revision `63e25e48c3af73db324ce61d0dba9cce`。
  - `conan download libxext/6.4.0 -r=ohpcd --only-recipe` 仍返回 `system acceleration policy not enabled`。
  - `origin/main` 已包含 `archives/l/libXext/6.4.0`，其 `conanfile.py` 实际 Conan 名称为 `libxext/6.4.0`，版本含义是历史 ABI `libXext.so.6.4.0`，上游源码为 `libXext 1.3.6`。
  - 将 `origin/main:archives/l/libXext/6.4.0` 导出到本机 Conan cache 后，`conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 通过，图中 `libxext/6.4.0` 被标记为 `Build`，说明 recipe 可解析但当前本机 cache/remote 没有匹配二进制。
  - 2026-08-11 再复检: `libxext/6.4.0` 已发布到 `ohpcd`，recipe revision `20942ab436730e84acb01dcf565fda68`，OHOS armv8 package `e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab` 可列出。

2026-08-10 追加验证:
- `conan inspect .` 通过。
- `conan source` 在 `D:\harmonyos\tmp\libxscrnsaver-source-check-*` 临时目录通过，源码下载与 sha256 校验成功。
- `python -m py_compile conanfile.py test_package/conanfile.py` 通过。
- `commands.json`、`manifest.yaml`、`conandata.yml`、`test_package/MANIFEST.yml` JSON/YAML 解析通过。
- `conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 通过；图中 `libxscrnsaver/1.2.5` 与 `libxext/6.4.0` 均标记为 `Build`，`libx11/6.4.0` 为 `Cache`。
- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 已执行到安装依赖阶段；随后 Windows 本机尝试补构缺失的 `libxext/6.4.0`，在执行 Autotools `configure` 时报 `'.' is not recognized as an internal or external command` 后失败。该失败点属于依赖 binary/执行环境阻塞，不是 `libxscrnsaver` recipe 语法或依赖图解析失败。
- 2026-08-11 复检 `conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` 通过；图中 `libxext/6.4.0#20942ab436730e84acb01dcf565fda68:e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab` 标记为 `Download (ohpcd)`。

2026-08-10 OHOS 设备单包构建:
- 远端机器: `currentUser@frp-tip.com:33332`
- 远端仓库: `/storage/Users/currentUser/validation/build_in_harmonyos`
- 执行命令:

```sh
CI_PACKAGES="archives/l/libxscrnsaver/1.2.5" zsh ci/conan/build_and_test.sh
```

- 结果: `Build Summary` 显示 `Total: 1`, `Success: 1`, `Failed: 0`。
- L0: pass。执行时 L0i 曾警告 `libxext/6.4.0` dependency NOT in registry；2026-08-11 已复查确认 `libxext/6.4.0` 发布到 `ohpcd`。
- L1: pass。`test_package` 编译并执行，输出 `libxscrnsaver API smoke passed`；L1e negative test 也确认测试依赖真实 lib/include。
- L2: skip，原因是 library package 无 `bin/`。
- L4: pass，no patches。
- L5: pass，`lib/` 有内容；包内包含 `lib/libXss.so*`、`include/X11/extensions/scrnsaver.h`、`lib/pkgconfig/xscrnsaver.pc`。
- 生成包引用: `libxscrnsaver/1.2.5#795ecef11c8fcf464695e272d2bac58b:1b58b9b3d9dee5c40cc6ead19c9269bd97d854ce#7b2a3f1c3721261beb46486d474ad213`。

2026-08-11 OHOS 设备单包复跑:
- 远端机器: `currentUser@frp-tip.com:33332`
- 远端仓库: `/storage/Users/currentUser/validation/build_in_harmonyos`
- 执行命令:

```sh
CI_PACKAGES="archives/l/libxscrnsaver/1.2.5" zsh ci/conan/build_and_test.sh
```

- 结果: `Build Summary` 显示 `Total: 1`, `Success: 1`, `Failed: 0`。
- L0: pass；依赖检查中 `libx11/6.4.0`、`libxext/6.4.0`、`xorgproto/2025.1` 均为 registry ok。
- `libxext/6.4.0#20942ab436730e84acb01dcf565fda68:e647863c487673f3505fad09e4305079038bb22d#b056ec34282b1e4cef84cb5be71b6aab` 从 `ohpcd` 下载。
- L1: pass。`test_package` 编译并执行，输出 `libxscrnsaver API smoke passed`；L1e negative test 也确认测试依赖真实 lib/include。
- L2: skip，原因是 library package 无 `bin/`。
- L4: pass，no patches。
- L5: pass，`lib/` 有内容。
- 生成包引用: `libxscrnsaver/1.2.5#795ecef11c8fcf464695e272d2bac58b:1b58b9b3d9dee5c40cc6ead19c9269bd97d854ce#b5fb0c45514f7518f1f75f01616d0ff3`。

## 下一步命令
复跑单包验证:

```sh
CI_PACKAGES="archives/l/libxscrnsaver/1.2.5" zsh ci/conan/build_and_test.sh
```

如使用 shadow CI runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/libxscrnsaver/1.2.5
```

提交前确认:
- `Build Summary` 只包含 `archives/l/libxscrnsaver/1.2.5`。
- L0/L1 通过。
- L5 中 `lib/libXss.*` 与 `include/X11/extensions/scrnsaver.h` 存在。
- `libxext/6.4.0` registry 状态已在 2026-08-11 确认发布。
