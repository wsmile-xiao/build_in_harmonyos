# 原生构建预先设置 CMAKE_SYSTEM_NAME 会使 try_run 被当成交叉编译

配对条目：`knowledge/drafts/DRAFT-minia-3.2.6-preset-system-name-false-cross.kv`
来源：minia 3.2.6 适配（2026-10-04），对照日志在 HarmonyOS 真机 `~/work/psj/`。
查重基准：`origin/main` `1262b4ac24a3244f254c3e8163fa35d04b48f7fb`。

## 问题

minia 3.2.6 捆绑的 HDF5 在配置阶段执行 `try_run`。真机命令行带
`-DCMAKE_SYSTEM_NAME=HarmonyOS` 与 `Platform/HarmonyOS.cmake` 时，配置失败。
原样日志（`minia8879-create-r2.log`，保存为 `minia8879-create-r2-harmony-cross.log`）：

```text
CMake Error: try_run() invoked in cross-compiling mode, please set the following cache variables appropriately:
-- Performing TEST_LFS_WORKS... no
Width test failed with result: PLEASE_FILL_OUT-FAILED_TO_RUN
-- Configuring incomplete, errors occurred!
CREATE_EXIT:1
```

同一台机器把系统名改成 Linux 时，`try_compile` 能通过，`try_run` 仍报
`invoked in cross-compiling mode` 与 `PLEASE_FILL_OUT-FAILED_TO_RUN`。
`uname -s` 为 HarmonyOS，编译器是本机 OHOS SDK Clang 15.0.4。

## 根因

设备上 CMake 4.4 的 `CMakeDetermineSystem.cmake` 写明：若 `CMAKE_SYSTEM_NAME`
已经有值，且 `CMAKE_CROSSCOMPILING` 未定义，就执行 `set(CMAKE_CROSSCOMPILING TRUE)`。
这里不判断该名字是否等于 `CMAKE_HOST_SYSTEM_NAME`。

因此两条看起来相反的写法结果相同：

- `-DCMAKE_SYSTEM_NAME=Linux`：宿主名仍是 HarmonyOS，名字不同，交叉标志为真。
- `-DCMAKE_SYSTEM_NAME=HarmonyOS`：名字与宿主相同，但因为是预先写入的，交叉标志仍为真。

HDF5 看到交叉标志后不运行探针，只留下 `PLEASE_FILL_OUT-FAILED_TO_RUN`。
嵌套检查仍会打印 `System is unknown to cmake, create: Platform/HarmonyOS`。
那条警告不是这次配置退出的原因。退出点是 `try_run` 拒绝执行。

独立探针（同一 Conan 工具链，不传 `CMAKE_SYSTEM_NAME`）打印：

```text
-- HOST=HarmonyOS
-- SYS=HarmonyOS
-- PROC=aarch64
-- CROSS=FALSE
-- TRY compile=TRUE run=0
```

显式带上系统名再加 `-DCMAKE_CROSSCOMPILING=FALSE` 时，探针同样是 `CROSS=FALSE`、`run=0`。
这与源码里“仅当变量未定义才强制为 TRUE”一致。

## 最小解决与边界

推荐做法是不预先设置 `CMAKE_SYSTEM_NAME`。Conan 工具链会把生成器目录前置到
`CMAKE_MODULE_PATH`。在该目录写入：

```cmake
set(UNIX 1)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
include(Platform/Linux)
```

CMake 随后采用宿主名 HarmonyOS，交叉标志保持假，`try_run` 在本机执行。
不要把系统名改成 Linux，也不要为 `PLEASE_FILL_OUT` 填写猜测的退出码。
补丁与这条 CMake 逻辑都不使用 `__OHOS__`。

若工具链必须在 `project()` 之前写入与宿主相同的系统名，才同时传入已经定义的
`-DCMAKE_CROSSCOMPILING=FALSE`。产物若不能在当前机器执行，不要使用这个开关。

## 验证

去掉 `-DCMAKE_SYSTEM_NAME` 后的同机 `conan create`（配方 md5 `275d3102356879e6c789ca9cfbd3301b`）配置片段：

```text
cmake ... -DHDF5_BUILD_TOOLS="OFF" ... -DCMAKE_POLICY_VERSION_MINIMUM="3.5"
-- Performing TEST_LFS_WORKS... yes
-- Performing Other Test HAVE_OFF64_T - Success
-- Performing Other Test HAVE_STAT64_STRUCT - Success
-- Configuring done (172.9s)
```

失败对照里这三项分别是 `no`、`Failed`、`Failed`，并伴随宽度测试 `FAILED_TO_RUN`。
修复后的命令行没有 `CMAKE_SYSTEM_NAME`。同一日志继续到 `[100%] Built target minia`。
`bash simple_test.sh` 打印四行 `PASSED`（X 场景按上游脚本先打印 `NOT EQUAL: 1 sequence(s)`，随后打印 `  6`）。
包 ID `d19813127f0ec2ca84c0b48cbd85080965097448`，`CREATE_EXIT:0`（2026-10-04T08:36:37Z）。
独立探针 `minia8879-cmprobe2/d.log`（工具链、不预置系统名）与 `e.log`（另加已定义的 `CMAKE_CROSSCOMPILING=FALSE`）都打印 `CROSS=FALSE` 与 `TRY compile=TRUE run=0`。`e/CMakeCache.txt` 中 `CMAKE_SYSTEM_NAME=HarmonyOS` 且 `CMAKE_CROSSCOMPILING=FALSE`。

## 与既有知识的关系（七轴查重）

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | 否 | `origin/main` `1262b4ac` 全树对 `FAILED_TO_RUN`、`PLEASE_FILL_OUT`、`TEST_LFS_WORKS`、`Width test failed`、`streampos` 为零命中。正式条目 542 个 `.kv`、542 篇 `doc` |
| causal_duplicate | 否 | 正式图谱里 `try_run` 只在 E459（MySQL 客户端图裁剪）。无 `graph/E603.kv`。草稿 E603 是另一台机器上的真交叉。宿主门禁草稿是名称不匹配后 `return()` |
| trigger_overlap | 部分 | `try_run() invoked in cross` 只命中 `knowledge/drafts/E603-draft-7C2A.md`。`PLEASE_FILL_OUT-FAILED_TO_RUN` 全树零命中 |
| solution_overlap | 部分 | `Platform/HarmonyOS.cmake` 与 E092、E383 的平台模块同名，那些条目修未知平台或 SONAME。本条新增的是不要预置 `CMAKE_SYSTEM_NAME`。正式图谱 `CMAKE_CROSSCOMPILING` 零命中 |
| combination_novelty | 是 | 预置 HarmonyOS 与预置 Linux 都是 `CREATE_EXIT:1`。只放 shim、不预置名字后 `TEST_LFS_WORKS` 为 yes，且 `CREATE_EXIT:0` |
| boundary_novelty | 是 | 边界是探针能否在当前机器执行，不是把 `System is unknown to cmake` 消掉 |
| test_migration_novelty | 是 | 证据是 HDF5 的 `TEST_LFS_WORKS` 与 `minia8879-cmprobe2` 的 hello `try_run`，不是 minia 的 test_package |

`streampos` 在 `knowledge/` 零命中。那是另一处 libc++ 编译问题，不并入本条。

**决定：** new_draft

## 适用边界与反例

适用：HarmonyOS 真机使用本机 SDK Clang 做原生配置，上游 `try_run` 必须拿到真实退出码。
反例：从 Windows 或 x86_64 Linux 交叉到设备时，`CMAKE_CROSSCOMPILING=TRUE` 是对的。
此时应沿用 E603，关闭可选探测或在设备上采集退出码，不能把交叉标志改成假，也不能填写 `PLEASE_FILL_OUT`。
反例：只想消除 `System is unknown to cmake` 警告、工程并没有 `try_run`。那是 E092 与已有 Platform 模块草稿的范围。
反例：上游用 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 做组件门禁并静默 `return()`。那是宿主门禁草稿，本条不改那些正则。
