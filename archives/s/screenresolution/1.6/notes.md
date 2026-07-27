# screenresolution 1.6 适配前置记录

## 基本信息

- 目标库: screenresolution
- 版本: 1.6
- 上游: https://github.com/jhford/screenresolution
- tag: v1.6
- commit: 8129f9d5b13c6cb43861c9277f74e7ebc5cd53ba
- 源码包: https://codeload.github.com/jhford/screenresolution/tar.gz/refs/tags/v1.6
- sha256: d3761663eaf585b014391a30a77c9494a6404e78e8a4863383e12c59b0f539eb
- issue: #1427
- AgentID: F72D
- worktree: D:\harmonyos\worktrees\screenresolution
- 分支: feat/screenresolution-1.6

## W0 依赖检查

上游 1.6 没有普通三方库依赖，但原实现直接依赖 Apple 平台框架:

- `Foundation.framework`
- `ApplicationServices.framework`
- `<ApplicationServices/ApplicationServices.h>`
- CoreGraphics display APIs, including `CGGetActiveDisplayList`, `CGDisplayCopyDisplayMode`, `CGDisplayCopyAllDisplayModes`, `CGConfigureDisplayWithDisplayMode`

这些不是可通过 Conan 单独发布的普通依赖，因此不拆依赖库适配。当前方案新增 OHOS 后端，使用系统库:

- 头文件: `<window_manager/oh_display_manager.h>`
- 库: `libnative_display_manager.so`
- API: `OH_NativeDisplayManager_GetDefaultDisplayWidth`, `OH_NativeDisplayManager_GetDefaultDisplayHeight`, `OH_NativeDisplayManager_GetDefaultDisplayRefreshRate`

官方文档说明该 NativeDisplayManager C API 起始版本为 12，能获取默认屏幕宽、高、刷新率；没有在该只读后端中映射物理分辨率设置能力。

## 源码与构建系统分析

- 构建系统: 纯 Makefile。
- 产物: `screenresolution` 命令行工具。
- 上游 macOS 链接命令: `clang ... -framework Foundation -framework ApplicationServices ...`
- 上游测试: `make test`，会真实更改显示器分辨率，并假设双显示器和固定分辨率。

本轮新增补丁:

- `patches/0001-add-ohos-display-backend.patch`

补丁内容:

1. Makefile 新增 `OHOS=1` 构建分支，构建 `main_ohos.o` 并链接 `-lnative_display_manager`。
2. 新增 `main_ohos.c`。
3. OHOS 支持:
   - `screenresolution -version`
   - `screenresolution get`
4. OHOS 明确不支持:
   - `screenresolution list`: 当前只读后端未枚举完整可切换模式。
   - `screenresolution set`: NativeDisplayManager 只读默认屏信息 API 没有等价物理模式 setter。

## Conan 配方状态

配方已从“OHOS invalid”改为“OHOS 构建候选”:

- `validate()` 接受 `Macos` 和 `OHOS`，拒绝 `Linux` 及其他未实现后端的平台。
- OHOS build 使用 Conan profile 中 `tools.build:compiler_executables` 指定的 clang。
- OHOS build 显式传入 `ARCH_FLAGS=""`，避免上游 macOS universal binary flags 污染 OHOS 编译。
- OHOS package 直接复制二进制到 `bin/`，并在真机 worker 上有签名工具时自签 ELF。

`test_package` 在 OHOS 上执行 `test.sh`，断言:

1. `-version` 输出 `screenresolution version 1.6`。
2. `get` 输出 `Display 0: <width>x<height>x32@<refresh>`，宽高刷新率为正整数。
3. `set 800x600x32` 必须失败，并输出 OHOS NativeDisplayManager backend 不支持设置模式的说明。

## 本机前置验证

已完成:

- 项目内搜索 `screenresolution`，未找到现有归档；后续用户确认 issue 为 #1427。
- 上游 tag 检查，选择正式 tag `v1.6`。
- 源码包下载并记录 sha256。
- 源码解包和构建系统检查。
- 官方 API 文档核对 `oh_display_manager.h` 的默认屏宽、高、刷新率接口。
- 准备 OHOS NativeDisplayManager 只读后端补丁。

已执行本机轻量复查:

```powershell
cd D:\harmonyos\worktrees\screenresolution\archives\s\screenresolution\1.6
python -m py_compile conanfile.py test_package/conanfile.py
conan inspect .
conan export . --user=ohpcd --channel=stable
```

结果:

- `python -m py_compile conanfile.py test_package/conanfile.py`: pass
- `conan inspect .`: pass，能读取 patch 列表和基础元数据。
- `conan export . --user=ohpcd --channel=stable`: pass，导出 revision `79ab79e3c9f829a9b89b68bb7d17b9d0`。
- `git apply --check patches/0001-add-ohos-display-backend.patch`: pass，仅提示临时解包目录中 `Makefile` 文件模式为 100644 而 patch 记录为 100755。

已执行本机 OHOS profile 短路验证:

```powershell
conan create . --user=ohpcd --channel=stable `
  -pr:h=D:\harmonyos\worktrees\screenresolution\ci\conan\profiles\ohos-aarch64 `
  -pr:b=D:\harmonyos\worktrees\screenresolution\ci\conan\profiles\ohos-aarch64 `
  --build=missing
```

结果:

- 通过 dependency graph；不再返回 `Invalid`。
- 通过源码下载和 `screenresolution-1.6.tar.gz` 解包。
- 通过 `apply_conandata_patches()`，`0001-add-ohos-display-backend.patch` 已成功应用。
- 在 Windows 本机执行 `make clean` 失败，错误为 `'.' is not recognized as an internal or external command`。这是非真机/非 zsh 构建环境边界；真正编译结论以后续真机验证为准。

## 真机 / shadow CI

后续如需复跑单包验证，命令为:

```sh
CI_PACKAGES="archives/s/screenresolution/1.6" zsh ci/conan/build_and_test.sh
```

或 shadow CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/s/screenresolution/1.6
```

验证重点:

- L0/L1 能进入 OHOS build，而不是 validate invalid。
- 链接 `libnative_display_manager.so` 成功。
- 二进制签名后能执行。
- `test_package/test.sh` 三项断言通过。
- `list`/`set` 的 unsupported 行为不会被误判为功能通过。

## 路径 B 候选判断

当前增强方案已具备路径 B 候选交付基础。理由详见 `reports/path-b-candidate.md`。

已补齐:

1. 真机 `screenresolution get` 输出证据。
2. 真机 `test_package` 通过证据。
3. `test_package` 同时覆盖 `list` 和 `set` 的 unsupported 负向断言，不冒充完整 macOS 功能等价。
4. 新增与 screenresolution 直接相关的知识草稿: `knowledge/graph/draft/E240-draft-F72D.kv`，主题为“macOS CoreGraphics 显示工具向 OHOS NativeDisplayManager 的能力分层迁移”。

## 2026-07-25 true-device validation update

User later confirmed the device window was free, so true-device heavy validation was executed.

Run directory:

```text
/storage/Users/currentUser/ohos-test-runs/codex-1.6-screenresolution-1.6-native-display-conan-20260725-174545-48199
```

Command:

```sh
sh /storage/Users/currentUser/ohos-users/codex/screenresolution-1.6-native-display/run-conan-heavy.sh
```

Result:

- exit code: 0
- L0_RESULT=pass: all checks passed
- L1_RESULT=pass: test_package executed
- L2_RESULT=skip: upstream CLI uses `-version`, not `--version`/`--help`; non-blocking
- L4_RESULT=pass: patches clean
- L5_RESULT=pass: bin/ has content

Runtime evidence:

```text
screenresolution version 1.6
Display 0: 3120x2080x32@60
Error: list is not supported on OHOS NativeDisplayManager backend: the public C API used here exposes current default-display metrics, not the full switchable mode list
Error: set is not supported on OHOS NativeDisplayManager backend: the public C API used here does not expose a physical display mode setter
```

Path B status after validation:

- Candidate is now supported by true-device evidence for the implemented OHOS capability boundary.
- Implemented OHOS capability: `-version` and `get`.
- Explicitly unsupported on OHOS: `list` and `set`.
- Negative unsupported behavior is covered by `test_package/test.sh`.
- Knowledge draft: `knowledge/graph/draft/E240-draft-F72D.kv`.
- Issue: #1427.
