# QBDI

QuarkslaB Dynamic binary Instrumentation（QBDI）是一个基于 LLVM 的**动态二进制
插桩框架**：把目标函数编译成插桩后的代码块，在运行期写入可执行内存并跳转执行，
同时维护指令缓存与指令重写规则。

- 上游：https://github.com/QBDI/QBDI
- 许可证：Apache-2.0

## 功能范围

- **可嵌入的进程内 VM**：`QBDI::VM` 直接在当前进程内插桩并调用目标函数
  （`addInstrumentedModule*` + `vm.call()`），无需外部调试器。
- **指令级回调**：`PREINST` / `POSTINST` 等事件回调，可读改 `GPRState` /
  `FPRState`。
- **指令重写与补丁**：对不认识的指令维护重写规则
  （`src/Patch/AARCH64/`、`src/ExecBlock/AARCH64/`）。
- **自有私有 LLVM**：上游明写使用**未被常规 LLVM 安装导出的私有 API**，
  因此 `cmake/llvm/QBDI_llvm.cmake` 钉住 `LLVM 19.1.5` 并经 FetchContent
  取**源码**编译，再由 `cmake/merge_archives.cmake` 合并进 `libQBDI.a`。

## OHOS 适配

- **构建期代码生成器**：LLVM 的 TableGen（`llvm-tblgen` / `llvm-min-tblgen`）
  必须能在鸿蒙 PC 上**原生执行**；本适配中它正常工作，是 872 个 ninja 目标里
  最先跑起来的一批。
- **四个平台阻碍**（均在设备上复现并解决）：
  1. LLVM 的 `config.guess` 不认识 HarmonyOS，而 `config-ix.cmake` 无条件调用
     `get_host_triple()`（`LLVM_HOST_TRIPLE` 是**输出**）→ configure 中止。
  2. LLVM 的 `NATIVE` TableGen 子构建重新识别 host 为 HarmonyOS，而 CMake
     没有 `Platform/HarmonyOS` 模块 → `UNIX` 未置位 →
     `HandleLLVMOptions.cmake` 报 "Unable to determine platform"。
  3. `cmake/merge_archives.cmake` 拒绝 `CMAKE_SYSTEM_NAME=HarmonyOS`。
  4. `config.guess` 需要非 HMDFS 的可写 `TMPDIR`。

  前两项由 `fixups/` 下两个**幂等 Python 脚本**解决，它们在 LLVM FetchContent
  解包之后、configure 之前被钩进 `cmake/llvm/QBDI_llvm.cmake`；钩子由
  `build()` 直接文本编辑写入，**不依赖外部 `patch` 工具**（`patches: {}` 为空）。
  第三项用 `-DCMAKE_SYSTEM_NAME=Linux`——这是正确的旋钮，鸿蒙 PC 的 ABI
  本就是 Linux（musl，`aarch64-unknown-linux-ohos`）。
- **运行期能力实测**：鸿蒙 PC 普通用户可用 **RWX `mmap`** 与 `mprotect`
  （插桩代码块执行的前提），但 **`ptrace` 被拒绝**（`AF_PACKET`/`SOCK_RAW`、
  `AF_INET`/`SOCK_RAW`、`NETLINK_XFRM` 同样被拒绝）。因此本适配与验证
  **只主张进程内嵌 VM 模式**；preload / 外部 attach 依赖 `ptrace`，
  属平台能力边界，不属适配缺陷。
- **配方层**：`validate()` 接受 `Linux` 与 `OHOS`（R32）并限定 AArch64；
  编译器取自 `tools.build:compiler_executables`（R33）。
  `QBDI_TOOLS_FRIDAQBDI` / `QBDI_TOOLS_PYQBDI` 关闭（分别需 Frida 与
  Python 开发头，且会扩大包体），**核心库与全部测试不受影响**。
- **头文件陷阱**：公共头文件分两处——源码树 `include/`，以及 CMake 构建树中
  `configure_file()` 生成的 `QBDI/Config.h`、`QBDI/Version.h` 与按架构选择的
  `QBDI/State.h`、`QBDI/Options.h`。**只复制源码树的配方会产出无法编译的包**
  （`QBDI/Platform.h` 会 include `QBDI/Config.h`）。
- **上游测试计数口径**：Catch2 用例宏跨全部架构编写。全仓
  `TEST_CASE_METHOD` 共 **751** 个，其中 **582** 个位于 ARM/X86/X86_64 目录、
  本构建（`QBDI_ARCH=AARCH64`）永不编译；`751 − 582 + 16 = 185`，
  与真机 `QBDITest --list-tests` 输出**逐条吻合**。
  真机跑满 **185 个用例、86542 个断言、0 失败**。
- 未修改任何上游源码；未删除、跳过或放宽任何测试。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libQBDI.a` | 核心静态库（内嵌私有 LLVM 19.1.5） |
| `include/QBDI.h` | C++ 主入口 |
| `include/QBDI/*.h`、`*.hpp` | 公共头文件（含构建期生成的 Config/Version/State/Options） |
