# libplctag 2.6.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang/clang++（OHOS SDK 15.0.4）
- 状态: built

## 编译步骤

```bash
# 平台检测修复（知识 E092/E140：OHOS 下 CMAKE_SYSTEM_NAME=HarmonyOS 时 UNIX 为空）
cmake .. -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_EXAMPLES=1 -DBUILD_TESTS=1
make -j1        # 100% 构建成功
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake "Unsupported platform!"，make 无目标 | OHOS 平台名 HarmonyOS 下 CMake `UNIX` 变量为空，上游 `if(UNIX)` 分支落入 else | 配方注入 `CMAKE_SYSTEM_NAME=Linux`（E092/E140） |
| 2 | `ld.lld: undefined symbol: pthread_cancel` | OHOS musl libc 不实现 POSIX 线程取消（同 Android） | 补丁扩宽 `__ANDROID__` 守卫为 `__ANDROID__ || __OHOS__`，镜像 pthread_kill（草稿 DRAFT-libplctag-2.6.5-ohos-pthread-cancel-android-branch-mirror） |
| 3 | 上游 test_hashtable.c 未注册 + include 路径损坏（lib/、util/ 实际为 libplctag/lib、utils/） | 上游未维护该内部单元测试 | 补丁修复相对 include 路径，恢复编译运行（50 项断言通过） |

## 源码修改

- `patches/0001-src-platform-posix-platform.c.patch`：thread_kill() 平台守卫扩宽（portability，R8 例外：musl libc 探针）
- `patches/0002-src-tests-hashtable-test_hashtable.c.patch`：测试 include 路径修复（非平台宏）

## 依赖版本

- 无外部运行时依赖（仅 libc + pthread）
- 测试模拟器 ab_server 由本库源码构建；modbus_server 依赖 libmodbus（registry 无配方，未实例化）

## 验证结果

```bash
# 上游测试（run_local_tests.sh，本地模拟器 ab_server 驱动）
bash src/tests/run_local_tests.sh build/bin_dist  → 11 tests, 11 successes, 0 failures
# 独立测试程序（无 PLC 环境部分依赖真实网关，create 超时）
test_special / test_tag_type_attribute → OK
test_string / test_tag_attributes / string_standard / string_non_standard_udt → PLC 网关不可达 TIMEOUT
# 手动恢复的 upstream hashtable 单元测试（上游未注册 CMake）
test_hashtable.c（修复 include 路径后编译运行）→ PASS
```

## 测试统计（双口径，详见 reports/test-ledger.md）

- source_declared_total = 22（EXECUTABLES 并集 21 + test_hashtable.c）
- configured_executable_total = 21（R03 启用 BUILD_MODBUS_EMULATOR=1 + libmodbus 3.2.0，modbus_server 已实例化）
- executed_passed_total = 16（R02 的 14 + test_callback_ex_modbus + test_reconnect）；失败 6（真实 PLC 网关不可达）；未运行/未实例化 0
- 全量通过率 16/22 = 72.7%；实际执行集合通过率 16/21 = 76.2%

## 交付物

- libplctag_static.a / libplctag.so.2.6（libplctag_static.a 需 `LIBPLCTAG_STATIC=1` 定义使用）
- include/libplctag.h

## 注意事项

- 静态库输出名 plctag_static（libplctag_static.a），消费者需定义 `LIBPLCTAG_STATIC=1`
- 上游测试中依赖真实 PLC 网关（10.206.x.x）的用例在本环境不可运行，恢复条件：接入 PLC 网络
- R03：libmodbus 3.2.0 已发布到 ohpcd（2026-09-10），已启用 `BUILD_MODBUS_EMULATOR=1` 由上游源码构建 modbus_server（非独立三方包）并运行 test_callback_ex_modbus/test_reconnect 均 PASS
---

**编译结束**: 2026-09-11 03:57
**最终状态**: built
