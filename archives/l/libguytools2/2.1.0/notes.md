# libguytools2 2.1.0 适配笔记

## 编译环境
- 构建系统: **qmake**（Qt5 `.pro`；上游无 CMake/autotools，也无 install 规则）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 / clang++
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64)，`os=OHOS os.version=6.0`
- 状态: built

## 源码信息
- 包名: `tools-2.1.0.tar.gz`（项目名 libguytools，conan 包名 libguytools2）
- 官方源: https://downloads.sourceforge.net/project/libguytools/libguytools/LatestSource/tools-2.1.0.tar.gz
- sha256: `79562f8e8db0296da0f7ff612fd9db41ad454560cc32a307a24d15fda74f1d56`
  （与 SourceForge `best_release.json` 元数据一致，重新下载复核通过）

## 编译步骤

```bash
# 1) 生成上游缺失的版本 include（tools.pro 无条件 include 它）
#    不用 create_version_file.sh —— 该脚本依赖 Debian 的 debian/changelog
printf 'VERSION = 2.1.0\n' > libguytools_version.pro.inc

# 2) qmake 配置：显式指定 linux-clang mkspec 以匹配 conan clang 工具链
"$QT5_QBASE/bin/qmake" trunk.pro -spec linux-clang

# 3) 构建（QMAKE_STRIP="" 防止 strip —— OHOS 加载器拒绝 stripped ELF）
make -j1 QMAKE_STRIP=""
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Cannot read libguytools_version.pro.inc: No such file or directory` | `trunk.pro` → `tools.pro` 无条件 include 该文件，但它不在发布包内（需由 `create_version_file.sh` 生成，而该脚本读 Debian 的 `debian/changelog`） | 配方在 `build()` 内直接写出 `VERSION = <version>`；不使用上游脚本 |
| 2 | **首个真实编译错误**：`error: redefinition of 'sockaddr_storage'`（`toolsysinfo.cpp:40`） | OHOS sysroot 下 `<linux/if.h>` 经 `linux/socket.h` 重定义 `sys/socket.h` 已定义的 `struct sockaddr_storage`（知识 E091/E119） | 改用可移植的 `<net/if.h>`：源码只需 `struct ifreq/ifconf` 与 `SIOCGIF*/IFF_*`，`net/if.h` 全部提供（已实测）。**不用**平台宏守卫，避免非 OHOS 平台行为变化 |
| 3 | `make: dpkg-buildflags: No such file or directory`（非致命） | `tools.pro` 用 `$(shell dpkg-buildflags ...)` 取 Debian 打包标志 | 仅告警、不阻塞（qmake 变量取空值，编译正常）。未修改源码 |
| 4 | SONAME 为 `libguytools.so.5`（不合理） | Qt ≥ 5.15 的 qmake 用 `QT_VERSION` 推导共享库主版本 | `tools.pro` 显式 `VERSION = $$VERSION` → SONAME `libguytools.so.2` |
| 5 | `Unknown module(s) in QT: core` | qt5-qtbase 包内 `mkspecs/modules/*.pri` 记录的是**已消失的构建目录**绝对路径（且与本依赖图 package hash 不一致） | 把 `.pri` 复制到本包 build 目录、将路径改写为 qt5-qtbase 的 package 目录，再经 `QMAKEMODULES` 暴露给 qmake（参考 baka/2.0.4 配方） |
| 6 | 上游无任何 install 规则（`make install` 无目标） | `tools.pro` 未定义 `INSTALLS` | 补 `target.path`/`headers.path` 与 `INSTALLS`，装到 `lib/` 与 `include/libguytools/` |
| 7 | `ToolErrorGetMessage()` 未注册错误码时仍返回 `NO_ERROR` | 该函数在 `NO_ERROR` 与"未找到"两个分支都返回 `NO_ERROR`，把 `TOOL_ERROR_ENTRY_NOT_FOUND` 吞掉 | 修正为返回 `TOOL_ERROR_ENTRY_NOT_FOUND`，并允许 `ppMsg` 为空指针（否则 `*ppMsg` 解引用空指针崩溃）。此缺陷使各模块 `TOOL_CHK(ToolErrorRegisterError(...))` 的失败检测失效 |
| 8 | `get()` 报 `BadZipFile` | `.../tools-2.1.0.tar.gz/download` 结尾是 `/download`，无扩展名，conan 无法推断归档类型 | 改用 SourceForge 直链 `downloads.sourceforge.net/.../tools-2.1.0.tar.gz`（sha256 一致） |

## 源码修改（补丁）

| 补丁 | 内容 |
|------|------|
| `0003-toolsysinfo.cpp.patch` | `toolsysinfo.cpp`：`<linux/if.h>` → `<net/if.h>`（平台可移植，非平台宏） |
| `0002-tools.pro.patch` | `tools.pro`：显式 `VERSION`（修正 SONAME）+ 补 `INSTALLS`（库与公开头文件安装规则） |
| `0001-toolerror.cpp.patch` | `toolerror.cpp`：`ToolErrorGetMessage()` 传播 `TOOL_ERROR_ENTRY_NOT_FOUND`，`ppMsg` 允许为空 |

## 依赖版本

- `qt5-qtbase/5.15.2`（制品仓已发布，二进制已下载验证；`transitive_headers=True, transitive_libs=True`）
- 传递依赖: `zlib/1.3.1`、`dbus/1.14.10`、`expat/2.8.Z`（由 qt5-qtbase 引入，均已发布）

## 上游测试（真实执行）

### 上游测试清点（R51 第一步）

`tools-2.1.0.tar.gz` 解包后**不含任何测试**，清点证据：

| 清点项 | 结果 | 证据 |
|--------|------|------|
| `tests/` 目录 | 无 | `tar tzf tools-2.1.0.tar.gz` 全量清单 = COPYING / changelog / create_version_file.sh / 4 个 `.pro` / 5 个库 `.cpp` / `include/` 下 8 个头文件 |
| `test_*.cpp`、独立测试程序 | 无 | `find . -iname '*test*'` 零命中；5 个 `.cpp` 中 `int main(` grep 零命中（纯库，无可执行测试） |
| qmake `check`/`test` 目标 | 无 | `tools.pro` / `toolsstatic.pro` / `trunk.pro` 中 `grep -i 'test\|check'` 零命中 |
| Debian 上游打包 | 无测试目标 | sources.debian.org `libguytools2 2.1.0-1` 的 `debian/rules` 仅 `build` / `install` / `binary-*` |

⇒ `upstream_check_command` 与 `upstream_test_command` 为空、`upstream_tests: []`
（见 `test_package/MANIFEST.yml`），无上游测试可执行。

### 适配后的消费者功能测试（conan create 真实执行）

上游无测试可跑，因此提供**消费者功能测试**（而非常量/返回值断言）：
`test_package/test_libguytools2.cpp`（109 处 `Check()` 调用点），由 `conan create`
编译并真实执行 —— `test_package/conanfile.py` 的 `test()` 直接运行测试二进制，
逐项 PASS/FAIL 输出进入 CI 日志。实测 **127 项检查 / 127 通过 / 0 失败 / 0 跳过**。

| 模块 | 真实输入 → 真实结果验证 |
|------|------------------------|
| ToolError | 注册表生命周期（未 Init / 重复 Init / 重复注册）、消息查表、errno 翻译、`ToolErrorCheck()` 实际日志内容；含 **0001 补丁回归项**（未注册码 → `TOOL_ERROR_ENTRY_NOT_FOUND`、`ppMsg` 允许为空指针、`ToolErrorMessage()` → `[code]`） |
| t_Log | 真实日志文件落盘并读回：Debug/Info/Error 三等级路由标签（`Debug - ` / `Info  - ` / `Error - `）、printf 格式化、版本串、文件/函数/行号信息、单例拒绝语义、构造/析构写出的 open/close 标记 |
| ToolSysInfo | `ToolSysInfoUname()` 与**本进程真实 `uname(2)`** 逐字段交叉校验（sysname/release/machine/nodename）；MAC 的 `AddrStr` 与 `AddrVal[]` 逐字节交叉校验 |
| ToolCfg | 真实配置文件解析（`SECTION/ENDSECTION`；STRING/INTEGER/DOUBLE/PRESENCE/SET/HMS 全类型 + 十六进制/负数/双引号转义）；命令行选项与**命令行优先于配置文件**（BOTH_TWICE：实测 CLI 值胜出、低优先级赋值不计次）；`ToolCfgBuildTemplate()` 模板内容校验；10 类错误路径逐项校验**错误码 + 解析器日志 + 目标变量未被写入**（整数越界/非数字、字符串缺引号、SET 非法值、HMS 越界、非法 double、未知关键字、仅命令行参数写进配置文件、重复赋值、缺 `ENDSECTION`），另校验缺必填参数、未知段、配置文件不存在 |
| ToolSignal | 真实信号往返：`SIGHUP`（守护线程继续运行）与 `SIGTERM`（守护线程退出）均由守护线程投递给 handler；校验 **handler 与信号日志回调都运行在守护线程**（`pthread_self()` 与主线程不同） |
| HarmonyOS (OHOS) | `uname` 平台身份三重（HarmonyOS / HongMeng 内核 / aarch64）、`TMPDIR` 契约（已导出 + 指向 `/storage/` 用户存储）、OHOS 文件系统落盘读回、`net/if.h` ioctl 路径（**0003 补丁改动的代码路径**）MAC 枚举格式 |

- **版本一致性**：测试的 `EXPECTED_VERSION` 由 `test_package/conanfile.py` 传入
  **被测包版本**（`cmake.configure(variables=...)`），与库内编译的
  `LIBGUYTOOLS_VERSION`（来自 `tools.pro` 的 `VERSION`）比对。实测把期望版本改为
  `9.9.9` 时测试失败、退出码非 0 —— 对"打包了错误/陈旧库"具有真实检出能力。
- **失败即构建失败**：`test()` 直接运行测试二进制，退出码非 0 ⇒ `conan create` 失败。
- 鸿蒙特有行为（平台身份/TMPDIR/OHOS 落盘/net·if.h MAC 路径）在非 OHOS 主机上
  整组报告 1 项 SKIP（不失败），保证测试可移植。

## 验证结果

```bash
# conan create（真实执行，exit 0）—— 编译并运行 test_package 的消费者功能测试
$ conan create archives/l/libguytools2/2.1.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
[ 50%] Building CXX object CMakeFiles/test_libguytools2.dir/test_libguytools2.cpp.obj
[100%] Built target test_libguytools2
libguytools2/2.1.0 (test package): RUN: "./test_libguytools2"
...
=== 3. ToolSysInfo — system information
  PASS  Uname() contains the real sysname
  ...
==========================================================
checks: 127   passed: 127   failed: 0   skipped: 0
# exit code = 0

# 产物 SONAME
llvm-readelf -d lib/libguytools.so.2.1.0 | grep -E "SONAME|NEEDED"
# -> SONAME: libguytools.so.2
# -> NEEDED: libQt5Core.so.5, libc++_shared.so, libc.so
```

## 交付物

| 文件 | 说明 |
|------|------|
| `libguytools.so.2.1.0` (`libguytools.so.2` / `libguytools.so`) | 共享库，保留版本化 SONAME 布局 |
| `include/libguytools/*.h` | 8 个公开头文件 |
| `licenses/COPYING` | GPL-2.0-or-later |

## 注意事项

- 上游 `toolsysinfo.h` 的公开 API 使用 `QString` 但**未** include `<qstring.h>`，
  消费者需自行引入（本包未改动该头文件；test_package 中已显式 include）。
- R38：产物为纯库（无 `bin/` 可执行文件），**不需要** `commands.json`。
- `tools.pro` 中的 `dpkg-buildflags` 调用在非 Debian 环境仅产生告警，不影响构建。
---

**编译结束**: 2026-09-22 12:34
**最终状态**: built
