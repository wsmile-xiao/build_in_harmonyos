# canopenterm 2.03 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | canopenterm 2.03 |
| 上游 | https://github.com/CANopenTerm/CANopenTerm (tag v2.03) |
| 语言/构建 | C / CMake 3.16+ |
| 许可 | MIT |
| 用途 | CANopen 设备分析与配置工具（SDL3 终端 UI + codb2json CLI + 单元测试套件） |
| 适配路径 | 路径 A（基础适配）+ 路径 B（知识草稿 DRAFT-8959） |

## 依赖策略（关键点）

上游 CMake 用 ExternalProject 自带全部 8 个依赖源码并构建，**无一来自 registry**：

| 依赖 | 版本 | 产物 | OHOS 处理 |
|---|---|---|---|
| cJSON | 1.7.19 | libcjson.so | 传 toolchain；unversioned so + plain soname（仅 OHOS，`CJSON_OHOS_ARGS` 收进 `if(OHOS)` 分支，Linux native 保持默认版本化 `libcjson.so.1.7.19`） |
| CANvenient | 1.02 | libCANvenient.so | 传 toolchain + PATCH_COMMAND 打 3 个补丁（bionic socket 顺序等） |
| pocketpy | 2.1.8 | 静态 | 传 toolchain |
| inih | r58 | 静态 | 传 toolchain |
| isocline | 1.0.9 | 静态 | 传 toolchain（OHOS 无线程库 readline/history，isocline 自带行编辑） |
| Lua | 5.5.0 | 静态 | 传 toolchain |
| SDL3 | 3.4.12 | libSDL3.so | 传 toolchain + PATCH_COMMAND 打 4 个补丁（平台判定/pthread sysdeps） |
| cmocka | 1.1.7 | 静态 | 传 toolchain + 补丁把 __aarch64__ 加进 __WORDSIZE 64 位分支（纯特征检测） |

补丁注入机制：conan `apply_conandata_patches` 只作用于主源码；依赖源码补丁
由 0004/0005/0006 新增的 CMake 脚本在 `ExternalProject_Add(... PATCH_COMMAND ...)`
中应用（脚本内 `patch -p1`，先用 `patch -R --dry-run` 探测已应用则跳过，
OHOS 最小工具链 `patch` 无 `-N`，见 DRAFT-8959；幂等可重放）。

## 关键坑（详见 DRAFT-8959）

1. **OHOS 平台判定**：profile 设 `CMAKE_SYSTEM_NAME=HarmonyOS` → CMake `UNIX` 为 OFF，
   上游所有 `if(UNIX)` 平台分支全部落空。主 CMakeLists 加 `elseif(UNIX OR OHOS)`
   复用 linux 源文件集；Windows-only `icon.rc` 在 OHOS 置空（`CONSOLE_ICON` 变量）。
2. **ExternalProject 不继承 toolchain**：8 个 `ExternalProject_Add` 逐个显式
   `-DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}`，否则子构建退回 host 架构。
3. **bionic socket 顺序**：CANvenient SocketCAN 驱动 `<sys/socket.h>` 必须先于
   `<linux/can.h>`。
4. **cmocka __WORDSIZE**：启发式只认 x86_64/sparc，aarch64 会按 32 位重定义
   `uintptr_t` 与 OHOS 冲突。
5. **soname 链**：交叉构建无 soname 符号链接，依赖方引用 unversioned `.so` 名；
   cJSON/CANvenient/SDL3 强制 plain `DT_SONAME`。cJSON 的版本/soname flag
   （`ENABLE_CUSTOM_COMPILER_FLAGS=OFF`/`ENABLE_CJSON_VERSION_SO=OFF`/
   `-Wl,-soname,libcjson.so`）收进 `CJSON_OHOS_ARGS` 变量、仅在 `if(OHOS)` 分支
   设置——无条件传递会让 Linux native 构建从默认版本化 `libcjson.so.1.7.19`
   变成 unversioned，与 Linux 分支的 `CJSON_LIBRARY`/`BUILD_BYPRODUCTS` 预期
   不一致（回归风险）。
6. **运行时库路径**：上游 CMake 不输出 RUNPATH（实测 3 个可执行文件均无），
   recipe generate() 用 `CMAKE_EXE_LINKER_FLAGS=-Wl,-rpath,'$ORIGIN/../lib'`
   直传链接器（不可用 CMAKE_BUILD_RPATH，上游不读取；不可用 patchelf，见坑 9）。
   package 布局 `bin/ + lib/ + share/canopenterm/`（codb/dbc/eds 数据 +
   scripts + tests）。
7. **测试冒烟注意**：CANopenTerm 安装信号处理器捕获 SIGTERM，`timeout`
   默认 TERM 杀不掉 → test_package 用后台启动+存活判定+kill -9；其余
   带 `timeout` 的命令加 `-k` 兜底。
8. **脚本静默死**：`set -euo pipefail` 下 `var=$(…| grep | …)` 若 grep 无匹配
   （rc=1）整条赋值管道非零 → 脚本直接中止且无任何 FAIL 输出（cmocka 全过
   时无 "FAILED" 行必现）。解析类赋值一律 `|| true` 兜底 + `${var:-0}`。
9. **运行时库路径**：上游 CMake 不输出 RUNPATH，recipe generate() 用
   `CMAKE_EXE_LINKER_FLAGS=-Wl,-rpath,'$ORIGIN/../lib'` 直接传链接器
   （bin/+lib/ 布局）；**不可**事后用 patchelf 改 ELF——OHOS 内核拒执行
   patchelf 改过的二进制（EPERM，conan cache 里 126）。
10. **测试工作目录**：OHOS `/tmp` 只读，run_unit_tests 的数据副本工作目录
   由 test_package conanfile 传入 `self.build_folder` 下可写路径。

## 测试与验证

- **上游单元测试**：`run_unit_tests`（cmocka，185 例：buffer/can/codb/dbc/dict/nmt/
  os/pdo/scripts/sdo/table/test_report/wrapper；can_read/can_write 经 `-Wl,--wrap` 打桩，
  无需真实 CAN 设备）。OHOS 构建实测 **185/185 通过**（工作目录需含 codb/dbc/eds 数据）。
  用例数取数口径：`src/tests/run_unit_tests.c` 内 `cmocka_unit_test(` 注册数 =
  各 `test_*.c` 内 `void test_*` 函数定义数 = 185（一一对应，无 #ifdef 条件注册）。
- **test_package**（消费测试，19 断言）：产物完整性 9 项 + 3 库 SONAME +
  `codb2json` usage 冒烟 + `CANopenTerm -p` 启动冒烟（rc<126 即成功执行）+
  对打包产物运行 185 例上游套件并校验 PASSED==run（动态解析 `N test(s) run`）。
- **边界**：SDL3 GUI 交互（窗口/输入/串口枚举）在无显示 headless 环境只能验证到
  `-p` plain mode 启动与库加载，未做 GUI 交互级验证；SocketCAN 驱动 OHOS 无
  socketcan 内核支持，相关路径为 stub。
