# rcon 0.6 适配笔记

上游：n0la/rcon（Valve Source RCON 协议命令行客户端，BSD-2-Clause，C 语言，CMake 构建）。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: Apple clang 17（本机原生验证）/ OHOS SDK clang 15（交叉，CI 同源）
- 状态: built

## 编译步骤

原生验证（本机 macOS）：

```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/Users/metyierzhen/usr/local
cmake --build build -j4          # rcon + srcrcontest 均通过（-Wall -Werror 零警告）
ctest --test-dir build            # 1/1 Passed（srcrcontest）
cmake --install build --prefix <TEST_PREFIX>
# 产物: bin/rcon + share/man/man1/rcon.1
bin/rcon --help                   # 退出 0，输出用法
```

交叉（OHOS aarch64）：conan create 走 ohos-local profile（本地 SDK clang 15），
编译与链接验证；运行类步骤（ctest/test_package）因本机不能执行 OHOS 二进制而跳过
（`tools.build.cross_building:can_run=False`），CI 真机环境执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `PKG_CHECK_MODULES(BSD REQUIRED libbsd)` 强制要求 libbsd（OHOS 制品仓未发布，无法构建） | 上游在 CMake 检测不到 `arc4random_uniform` 时 REQUIRED libbsd；srcrcon.c 仅 `src_rcon_message_random_id()` 一处消费 `arc4random_uniform(INT32_MAX-1)`。实测 OHOS libc 已内建 `arc4random_uniform`（W3 日志 `Looking for arc4random_uniform - found`），回退为防御性代码 | 补丁 0002：srcrcon.c 增加基于 `arc4random()` 的拒绝采样回退 `rcon_arc4random_uniform()`（HAVE_ARC4RANDOM_UNIFORM 未定义时启用），移除 `<bsd/stdlib.h>` 硬包含；补丁 0001/0003：主 CMakeLists.txt 与 tests/CMakeLists.txt 移除 libbsd REQUIRED 与链接块。可移植纯 C 回退，无平台宏（R8） |
| 2 | CMake 4.x 报 "Compatibility with CMake < 3.5 has been removed" | 上游 CMAKE_MINIMUM_REQUIRED 3.1（主）/3.0（tests）过旧 | 补丁 0001/0003：两处最低版本提升至 3.5 |
| 3 | 初加 `tool_requires("pkgconf/3.0.5")` 后 macOS 本机 create 报 exec format error | ohpcd 的 pkgconf 是 OHOS 二进制，无法在 macOS 执行 | **不加 pkgconf tool_requires**：CI worker 与 macOS 均有系统 pkg-config（recc/1.4.13 同款先例证明 CI worker 无需 pkgconf）；配方 generate 里 PkgConfigDeps 暴露 .pc 给 pkg_check_modules |
| 4 | CI 真机 ctest 失败：srcrcontest 运行时 `Error loading shared library libcheck.so` + symbol not found（构建 #62755） | ①conanbuild env 不含 test-only 依赖（check）的 lib 路径，加载器落到系统 libcheck.so（符号不匹配）；②OHOS 目标 /tmp 只读（Check 0.15.2 先查 TEMP/TMP/TMPDIR）；③Check 的 fork 运行器在 HMDFS 上 IPC 文件权限异常 | 照 rgxg/0.1.2 已合入先例修复：`_check_run_prefix()` 为 ctest 运行注入 `LD_LIBRARY_PATH=<check libdir>` + `TEMP/TMP/TMPDIR=build/check-tmp` + `CK_FORK=no`（仅 OHOS） |
| 5 | CI 真机 ctest 真实断言失败（构建 #62807）：srcrcon_serialise_auth 的 `sz == auth->size + sizeof(auth->size)` 与 srcrcon_serialise_command 的 `buf[0] == cmd->size` 不成立（后续 id/type/payload 字段断言全过） | **OHOS musl 的 open_memstream 缺陷**：写入后**不 fflush 直接 fclose 不发布 buffer/size**（*sizep 滞留初值 0、buffer 内容未提交，POSIX 要求 fclose 隐式 flush，glibc/上游 musl 均正确）。rcon 的 `src_rcon_serialize` 恰是"fwrite...fclose...读 *sz/*buf"模式。知识库同因条目：DRAFT-E660（mustach，探针四象限：plain close sz=0 / fflush+close sz=N）、DRAFT-13533（lsquic，buffer 恒空） | 补丁 0002 追加：srcrcon.c 的 `src_rcon_serialize` 在 `fclose(str)` 前补 `fflush(str)`（一行平台适配，不改 API；macOS 原生 ctest 全绿验证无回归） |
| 6 | e2e 端到端消费者用例真机失败（构建 #63689）：`rcon` 客户端报 `Failed to receive data: Connection reset by peer` 后 SIGTRAP 崩溃 | **open_memstream 缺陷第二处**：`main.c handle_arguments` 用 open_memstream 拼接命令参数，同样 fclose 前无 fflush → OHOS 上命令体恒空，服务器校验失败断开 → 客户端读 RST → 崩溃 | 补丁 0002：`handle_arguments` 在 `fclose(cmd)` 前补 `fflush(cmd)`（同一行平台适配；macOS 原生 e2e 全绿验证无回归） |

## 源码修改

补丁由 `refresh-patch --auto` 生成（文件名按「序号-变更文件路径」命名）：

- `0001-CMakeLists.txt.patch`：主 CMakeLists.txt 移除 `PKG_CHECK_MODULES(BSD REQUIRED libbsd)` 硬依赖块；CMake 最低版本 3.1→3.5
- `0002-main.c.patch`：`handle_arguments` 的 open_memstream 在 fclose 前补 `fflush(cmd)`（OHOS musl 缺陷第二处，命令拼接体恒空导致 e2e 失败）
- `0003-srcrcon.c.patch`：新增 `rcon_arc4random_uniform()` 拒绝采样回退（基于 `arc4random()`，OHOS libc 实测已有 `arc4random_uniform`，回退仅作防御），移除 `<bsd/stdlib.h>` 硬包含；调用点按 `HAVE_ARC4RANDOM_UNIFORM` 分支；`src_rcon_serialize` 在 `fclose(str)` 前补 `fflush(str)`
- `0004-tests-CMakeLists.txt.patch`：tests/CMakeLists.txt 移除 BSD 链接块；CMake 最低版本 3.0→3.5

## 依赖版本

- glib/2.84.0.1（制品仓已发布，host 依赖）
- check/0.15.2（test_requires，上游测试框架）
- 不加 pkgconf tool_requires（CI worker 与 macOS 均有系统 pkg-config；初加 pkgconf/3.0.5 因 OHOS 二进制无法在 macOS 执行而移除）

## 验证结果

- 上游测试：tests/srcrcontest.c 共 61 个 ck_assert，ctest 1/1 原生通过（本机 Mac 实测）
- 原生构建 -Wall -Werror 零警告；rcon --help 退出 0
- 交叉编译：conan create（ohos-local）全链路编译验证

## 交付物

| 文件 | 说明 |
|------|------|
| bin/rcon | Source RCON 命令行客户端（--help/-h/-H/-P/-p/-c/-s/-m/-n/-d/-1） |
| share/man/man1/rcon.1 | 手册页 |
| share/bash-completion | 可选（INSTALL_BASH_COMPLETION=ON，默认 OFF 未启用） |

### 测试（test_package，鸿蒙特有测试）

| 用例 | 说明 |
|------|------|
| 冒烟 | `rcon --help` 断言退出码与用法输出 |
| 端到端消费者用例 | 本地起最小 RCON 服务器（127.0.0.1 真实 TCP socket），驱动 `rcon` 二进制完成真实 auth+command 往返：服务器校验 auth 报文（type=3、密码正确）与命令报文（type=2、payload 正确），客户端输出响应体 `e2e-ok` 且退出 0（评审规则 12 要求的完整消费者用例，非纯断言） |

## 注意事项

- R38：application 包，已提供 `archives/r/rcon/commands.json`（type=tool）
- 上游测试仅在 `can_run(self)` 时于 build() 内执行 ctest；CI 真机可跑，本地交叉环境跳过（已记录原因）
- glib 为 host 运行时依赖；check 仅为测试期依赖（test_requires，不进运行时图）
---

**编译结束**: 2026-09-27 14:16
**最终状态**: built
