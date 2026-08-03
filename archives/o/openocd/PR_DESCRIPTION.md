- **三方库名称**：openocd
- **上游版本**：0.12.0
- **上游仓库地址**：https://github.com/openocd-org/openocd
- **适配路径**：路径 A（基础适配）
- **使用知识库**：Autotools 构建，SourceForge release tarball 自带 configure 及子模块源码，需 patch 支持 OHOS 平台检测与 jimtcl 编译

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 主工程无独立单元测试框架 |
| 集成测试 | 1 | 上游 Autotools `make check` 目标（头文件独立编译检查，hermetic，已在 OHOS 沙箱构建阶段执行） |
| 子模块测试 | 90 | jimtcl（内置 TCL 引擎）tests/ 目录 90 个 Tcl 测试用例 |
| **合计** | **91** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 集成测试 | 1 | 不变 | `make check` 头文件独立编译检查，已在构建阶段执行 |
| 子模块测试 | 90 | 不变 | jimtcl 90 个 Tcl 测试，已在 OHOS 真机运行 |
| 消费者测试 | 1 | +1 | 验证 bin/openocd 存在且可执行（openocd --version 非交互模式） |
| **合计** | **92** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游仅有 `make check`（头文件独立编译检查，已在沙箱执行）；无实际运行的功能测试程序，适配后补全了消费者测试

> - **补全的测试范围**：为核心功能新增 1 个消费者测试
> - **补全原因**：openocd 为 JTAG 调试工具，实际调试需硬件，CI 沙箱中仅验证 CLI 基础功能
> - **新增测试文件清单**：
>   1. `archives/o/openocd/0.12.0/test_package/test.sh` — 验证 bin/openocd 存在、可执行且 --version 输出含 "Open On-Chip Debugger" 与版本号 0.12.0

## 验证结果

- 编译状态：通过（本地已验证 configure + make 编译成功，L0/L1/L2/L4/L5 全部通过）
- 上游测试执行情况：`make check`（头文件独立编译检查）已在 OHOS 沙箱构建阶段实际执行并通过（CI 门禁 L1c 确认）；jimtcl 子模块 90 个 Tcl 测试已在 OHOS 真机运行：**82 通过 / 8 失败**（失败用例 event/exec2/file/filecopy/interactive/posix/signal/socket，依赖信号、硬链接、套接字等 OHOS 受限内核能力，与 openocd 适配无关）
- 上游测试用例通过率：82/90（91.1%）
- 新增测试用例通过率：1/1（100%，本地已验证 test.sh 和 test_package 通过）

## 补充说明

- **构建系统**：Autotools（SourceForge 官方 release tarball 自带 configure，无需 autoreconf；GitHub tag tarball 不打包子模块源码且沙箱缺 aclocal）
- **内部子模块**：jimtcl（TCL 引擎，默认启用）已随 release tarball 打包；libjaylink 用 --disable-internal-libjaylink 禁用（仅部分适配器需要）
- **补丁**：
  - 0001-port-for-ohos.patch — build-aux/config.guess + config.sub 添加 HarmonyOS/OHOS 检测
  - 0002-jimtcl-export-cc.patch — jimtcl configure 导出 VAR=value 参数为环境变量，使 CC/CC_FOR_BUILD 生效
  - 0003-jimtcl-config-guess-ohos.patch — jimtcl autosetup-config.guess 添加 HarmonyOS/OHOS 检测
- **依赖**：无外部 Conan 依赖；USB 适配器驱动（libusb/hidapi/libftdi）均为可选，OHOS 沙箱未启用
- **commands.json**：已按 R38 规范创建（type: "tool"）
- **注意**：config.status 的 mktemp 临时目录在 OHOS 沙箱权限受限，配方已在 configure 前修复（同 flac 方案）
- **上游测试说明**：openocd 主工程无独立测试套件，`make check` 为头文件独立编译检查（已在构建阶段执行）；内置子模块 jimtcl 自带 90 个 Tcl 测试用例（tests/*.test），已在 OHOS 真机用 jimsh 运行，82/90 通过，8 个失败依赖信号/硬链接/套接字等 OHOS 受限内核能力（event、exec2、file、filecopy、interactive、posix、signal、socket），与 openocd 适配逻辑无关
