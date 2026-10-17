# znc-extra 1.10.2 适配笔记（HarmonyOS PC / arm64）

## 定位

Alpine `community/znc` 的 `extra()` 子包 —— 11 个模块 `.so`：
`autovoice` / `block_motd` / `clearbufferonmsg` / `ctcpflood` / `flooddetach` /
`imapauth` / `listsockets` / `log` / `notify_connect` / `send_raw` / `shell`。
znc 主程序、核心库 `libznc`、基础模块与头文件归 `znc` 主包，不在本子包内。

## 编译环境

- 构建系统: cmake（上游 CMake ≥3.15，本配方用 `moddisable_<模块>` 只构建 11 个模块）
- 编译日期: 2026-09-29
- 编译器: clang / clang++（OHOS SDK，aarch64-linux-ohos，libc++，cstd 17，Release）
- profile: `ci/conan/profiles/ohos-aarch64`
- 依赖: openssl/3.5.6、zlib/1.3.1.1（均在制品仓）
- 状态: built

## 编译步骤

```bash
# 1. 源码：https://znc.in/releases/archive/znc-1.10.2.tar.gz（2,313,233 bytes）
#    sha256 5b7561f3b100234d58ae4946eac0262ab305d275c094e64ae723e45d07be08ab
# 2. 生成/构建/打包（Conan 全流程）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init znc-extra 1.10.2
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify znc-extra 1.10.2
# 3. 收尾（W3 本地 CI 内含 conan create + test_package）
python3 $SKILL_ROOT/scripts/ohc-run.py finish znc-extra 1.10.2 built
```

关键 CMake 传参（配方 `generate()`）：

```
WANT_OPENSSL=YES  WANT_ZLIB=YES   # 仅保留模块语言无关依赖
WANT_CYRUS=NO WANT_ICU=NO WANT_ARGON=NO WANT_I18N=NO
WANT_PERL=OFF WANT_PYTHON=OFF WANT_SWIG=NO
moddisable_<其余 48 个模块>=true  # 逐个禁用非本子包模块
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake `try_compile` 探测 C++17 失败（首次配置） | CMake 无 `Platform/HarmonyOS.cmake`，交叉编译探针无法链接测试程序 | 补丁 0001：优先用编译器能力库 `CMAKE_CXX_COMPILE_FEATURES` 判定，能力库无法判定时才回退 `try_compile` |
| 2 | 链接 `znc` 可执行文件报 C++ 运行时符号未定义 | OHOS clang 不隐式追加 libc++ | 补丁 0002：链接行显式加 `-lc++` |
| 3 | 编译 `main.cpp` 报 `pthread_cancel` 未声明 | OHOS/musl 未提供 `pthread_cancel` | 补丁 0003：析构置 `m_stop` 后用线程定向信号唤醒信号线程 |
| 4 | `savebuff` 模块编译失败 | 依赖 OHOS libc 未提供的 `getpass()` | 该模块不属本子包，`moddisable_savebuff=true` 排除 |
| 5 | 宿主报 `No modules found`，模块装载后符号解析失败 | 宿主 `.dynsym` 未导出模块所需 ZNC 核心符号 | 宿主（znc 主包）链接加 `-Wl,--export-dynamic`；已作经验记录，属主包交付要求 |
| 6 | `~CSignalHandler()` 用 pipe 唤醒 `sigwait()` 无效（代码检视 P1） | pipe 由主线程 socket manager 的 `CSignalHandlerMonitorFD` 消费，与信号线程的 `sigwait()` 无关联；正常 SIGTERM/SIGINT 退出时无第二次信号 → `join()` 永久阻塞 | 补丁 0003 改用 `pthread_kill(thread, SIGUSR1)`（`sigwait` 等待集含 SIGUSR1）唤醒，`m_stop` 置位后线程直接返回 |

## 源码修改

仅补丁，无直接改源码（探索阶段改动已由 `refresh-patch --auto` 固化为补丁）：

- `patches/0001-cmake-TestCXX17.cmake.patch` — C++17 探针改为编译器能力库判定，`try_compile` 仅作回退
- `patches/0002-src-CMakeLists.txt.patch` — znc 可执行文件显式链接 libc++
- `patches/0003-src-main.cpp.patch` — 用原子标志 + 线程定向 SIGUSR1 替代 `pthread_cancel`

## 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| openssl | 3.5.6 | `WANT_OPENSSL`（模块 TLS/摘要相关） |
| zlib | 1.3.1.1 | `WANT_ZLIB`（模块压缩相关） |

## 验证结果

```bash
# W3 本地 CI（finish step 5/10，exit_code=0）
python3 $SKILL_ROOT/scripts/ohc-run.py finish znc-extra 1.10.2 built
# conan create：Package created，lib/znc/ 下 11 个模块 .so（共 13 个文件）
# conan test（test_package/test.c，34 断言）：12/12 行 PASS
# conan-verify：G0-G4 + L2/L4/L5 全 PASS
```

- 上游 gtest 套件（`test/`，14 个测试文件）**已真实构建并运行**：官方 tarball 未打包 gtest/gmock
  源码（`third_party/googletest` 为空目录、submodule 未纳入 `make dist`），按上游 submodule 约定
  补入 GoogleTest v1.17.0 官方源码（sha256 `65fab701…b27c`）后，`unittest_bin` 目标即生成。
  实测 **138 个用例 / 137 通过 / 1 失败**（`UtilsTest.Timezone`，设备缺 cctz 时区数据库
  `/usr/share/zoneinfo`，非适配缺陷；详见 `reports/test-report.md` §2/§2.1）。
  完整控制台日志本地存档 `reports/upstream-gtest-1.17.0.log`（`reports/` 属 AI 元数据，按仓库
  `.gitignore` 不入库；关键数据与逐字复现步骤见 `reports/test-report.md` §2）。
- 功能性验证：用同一 OHOS 工具链构建真实 `znc` 宿主进程，`dlopen` 装载本包 11/11 模块成功。

## 注意事项

- 本包无命令行工具（纯模块 `.so`），故无 `commands.json`。
- 模块以 `dlopen` 方式由宿主加载，配方 `package_info()` 不暴露 libdirs/bindirs/includedirs。
- 完整测试记录见 `reports/test-report.md`，W3 日志见 `reports/w3-local-ci.log`。
---

**编译结束**: 2026-10-01 17:50
**最终状态**: built
