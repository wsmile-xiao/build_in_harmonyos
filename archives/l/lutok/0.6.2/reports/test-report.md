# lutok 0.6.2 测试报告

> **项目**: lutok 0.6.2（Lua 5.3+ 的 C++ RAII 绑定库，FreeBSD/ATF 测试栈基础件）
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，musl libc，clang 15.0.4 / libc++）
> **测试类型**: 上游官方测试套件（6 个 atf-c++ 程序 + atf-sh examples_test，无 kyua 执行）
> 加 Conan 消费者测试（test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 101 | 100% |
| 通过 (PASS) | 101 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（101/101）**

> 口径：上游 6 个 atf-c++ 测试程序共 97 个用例（c_gate 2 / debug 2 /
> exceptions 4 / operations 19 / stack_cleaner 4 / state 66，按源码中
> `ATF_ADD_TEST_CASE` 清点）+ `examples_test`（atf-sh）4 个用例（真实编译并
> 运行 bindings/hello/interpreter/raii 四个上游示例）。kyua 在 OHOS 不可用，
> 使用 ATF 测试程序接口执行：`prog -l` 枚举（TP 格式 `ident:`）+ `prog <case>`
> 单用例运行，退出码 0 = 通过；运行日志见 `reports/atf-cxx-upstream-tests.log`
> 与 `reports/examples-upstream-tests.log`。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游测试套件在 OHOS 真机全量执行、全部通过；消费者测试
（`conan create` 的 L1 测试）真实调用公开 API 并断言行为，全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| config.guess 2018 版不识别 HarmonyOS | configure 直接失败 | 🔴（已修复：显式 --build/--host） |
| HMDFS 上 toybox `mktemp -d`（umask 077）目录不可写 | config.status 中断 | 🔴（已修复：mktemp shim） |
| atf/0.23 制品 `.la` 的 `dependency_libs=//lib/libatf-c.la`（prefix=/ 构建） | 测试程序链接失败 | 🔴（已修复：.a 拷贝目录） |
| atf-sh 编译期 `ATF_SHELL=/data/service/hnp/bin/bash` 不存在 | examples_test 无法启动 | 🟡（已修复：运行前设 ATF_* 环境） |
| lua 制品缺 `lua.hpp`（公开头需要） | 库与消费者编译失败 | 🟡（已修复：生成包装头并随包安装） |
| profile `cppstd=17` 压制上游强制 C++20 | 标准不匹配风险 | 🟡（已修复：extra_cxxflags 追加 -std=c++20） |

### 2.3 可用功能清单

```
✅ Lua state RAII 包装（state/operations/stack_cleaner/c_gate/debug/exceptions 全 API）
✅ Lua 脚本求值与原生函数绑定（do_string/pcall/create_module/push_cxx_function）
✅ C++ 异常 → lutok::error 转换
✅ C++20 构建（AX_CXX_COMPILE_STDCXX(20) 探测通过）
✅ 消费者视角：包含 <lutok/c_gate.hpp>（含生成 lua.hpp）链接 lutok 并运行
```

### 2.4 已知限制

1. 上游测试以 kyua 编排（`Kyuafile`）；kyua 尚未适配 OHOS，本轮以 ATF 程序
   接口逐用例执行（用例集合与 Kyuafile 注册的程序一致，无跳过项）。
2. `examples_test` 依赖已安装 lutok（pkg-config + make 编译示例），在
   `make install` 之后执行；交叉编译场景（`can_run=False`）会整体跳过并记录。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `c_gate_test`（2 用例） | Lua C API gate 与 connect | ✅ PASS |
| `debug_test`（2 用例） | get_info/get_stack 调试辅助 | ✅ PASS |
| `exceptions_test`（4 用例） | error/api_error/file_not_found_error 层次 | ✅ PASS |
| `operations_test`（19 用例） | create_module/do_file/do_string/eval（含错误路径） | ✅ PASS |
| `stack_cleaner_test`（4 用例） | RAII 栈清理（empty/some/nested/forget） | ✅ PASS |
| `state_test`（66 用例） | state 包装全 API（含 pcall/异常/栈平衡） | ✅ PASS |
| `examples_test`（4 用例） | atf-sh 编译并运行 bindings/hello/interpreter/raii | ✅ PASS |
| `conan create` → test_package | 消费者程序 `test_lutok`：6 处断言（do_string 求值=2、native 模块调用=42、stack_cleaner、失败脚本抛 lutok::error、state_c_gate 裸 lua_State） | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（101/101 全部执行）。

---

## 四、关键问题分析

### 问题 1: config.guess 无法识别 HarmonyOS

**现象**：
```
checking build system type... ./admin/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```
**根因**：release 附件内 config.guess（2018-08-29）不识别 `uname -s = HarmonyOS`。
**解决方案**：configure 显式传 `--build=aarch64-unknown-linux-gnu
--host=aarch64-unknown-linux-gnu`，不改上游文件。

### 问题 2: config.status 临时目录不可写（HMDFS + mktemp）

**现象**：
```
./config.status: line 872: ./confNKNiEl/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```
**根因**：Autoconf 2.72 的 config.status 以 `(umask 077 && mktemp -d ./confXXXXXX)`
建临时目录；HMDFS 上 toybox `mktemp -d` 在 umask 077 下产出的目录（drwx--S---）
不可写入（设备实测 `write_rc=1`），而 `mkdir` 产出的目录（drwxrws--x）可写。
**解决方案**：配方生成 mkdir 版 `mktemp` shim 并前置 PATH（skypat 3.2.0 同源
处置，本轮在 lutok 上独立复现并验证）。

### 问题 3: atf 制品 .la 的绝对/坏路径

**现象**：
```
libtool: warning: library '.../lib/libatf-c++.la' was moved.
libtool:   error: cannot find the library '//lib/libatf-c.la' or unhandled argument
```
**根因**：atf/0.23 制品以 `prefix=/` 构建，`.pc` 输出 `includedir=//include`，
`.la` 的 `dependency_libs` 指向 `//lib/libatf-c.la`（设备上不存在）。
**解决方案**：配方自写 `atf-c++.pc`/`atf-sh.pc`（指向 atf 包真实路径），并把
`libatf-c++.a`/`libatf-c.a` 拷贝到构建目录私有 link 目录供 `-L` 使用，绕开坏
`.la`；不改动依赖包。

### 问题 4: atf-sh 的编译期 shell 路径

**现象**：
```
Failed to execute /data/service/hnp/bin/bash: No such file or directory
```
**根因**：atf-sh 编译期默认 `ATF_SHELL=/data/service/hnp/bin/bash`（CI worker
路径），设备上不存在。
**解决方案**：运行 examples_test 前显式设置 `ATF_SHELL`（及
`ATF_LIBEXECDIR`/`ATF_PKGDATADIR`）指向设备真实路径。

### 问题 5: lua 制品缺 lua.hpp

**现象**：
```
.../include/lutok/c_gate.hpp:35:10: fatal error: 'lua.hpp' file not found
（以及消费者编译 c_gate.hpp 时的 lua.h 缺失）
```
**根因**：lua/5.4.8（及 5.4.8.1）制品只安装 `*.h` 与 liblua.a，未包含上游发行版
自带的 C++ 包装头 `lua.hpp`；lutok 的公开头 `c_gate.hpp` 及多个源文件依赖它。
**解决方案**：配方在私有 build prefix 生成标准四行包装头用于构建，并安装到包内
`include/lua.hpp`，保证消费者包含 `<lutok/c_gate.hpp>` 时可用（lua-rapidjson
0.6.0 同族先例）；不修改上游源码。

### 问题 6: C++20 与 profile cppstd=17

**现象**：上游 `AX_CXX_COMPILE_STDCXX(20, noext, mandatory)` 把 `-std=c++20`
追加进 `CXX`；而 conan `CXXFLAGS` 中 profile 的 `-std=c++17` 位置更靠后
（后出现者生效），标准可能被压回 C++17。
**解决方案**：`tc.extra_cxxflags.append("-std=c++20")` 置于标志列表尾段，
保证最终编译标准为 C++20（实测编译命令以 `-std=c++20` 收尾）。

---

## 五、测试环境

```
设备: HarmonyOS PC（aarch64，HongMeng Kernel 1.12.0）
编译器: clang/clang++ 15.0.4（OHOS SDK），libc++（-stdlib=libc++）
Conan: 2.29.1（OHOS 适配版），profile ohos-aarch64-device
依赖: lua/5.4.8（静态库）, atf/0.23（test_requires，静态库）
构建: ./configure --prefix=<pkg> --build=aarch64-unknown-linux-gnu
      --host=aarch64-unknown-linux-gnu --enable-atf --with-doxygen=no
      --enable-shared --disable-static; make -j1
测试: prog -l 枚举 + prog <case> 逐用例执行（97 + 4 = 101）；conan create test_package
```

---

*报告生成时间: 2026-09-17*
