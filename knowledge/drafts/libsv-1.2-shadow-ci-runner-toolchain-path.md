# 真机 shadow CI：runner 启动会话缺工具链 PATH 导致 cmake exit 127

> 草稿（DRAFT）。与同目录 `libsv-1.2-shadow-ci-runner-toolchain-path.kv` 成对。

## 适用场景

在鸿蒙 PC 真机上跑 shadow CI（`ohos-test-runner.sh --mode heavy` →
`zsh ci/conan/build_and_test.sh`），配方为 **CMake 类**（build() 里
`cmake.configure()`）且**无 cmake 的 tool_requires**（依赖系统 PATH 里的 cmake）。

## 现象

```text
libsv/1.2: RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=... ...
/system/bin/sh: cmake: inaccessible or not found
ERROR: libsv/1.2: Error in build() method, line 48
	Conmake.configure() ... ConanException: Error 127 while executing
[fail] libsv/1.2 — conan create failed
L1_RESULT=fail: conan create failed
```

注意：conan 依赖图计算正常（编译器由 profile 的
`tools.build:compiler_executables` 绝对路径提供，**不需要** PATH），
source() 下载也正常——只在 `cmake.configure()` 才 127。

## 根因

- 真机的 cmake/ninja/make 位于 `/data/service/hnp/bin`（cmake 4.1.2），
  **不在** runner 继承的默认 PATH（`/bin:/usr/bin:/sbin:/usr/sbin` +
  `~/.local/bin` + `~/usr/local/bin`——后两者也没有 cmake）。
- `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 里
  `PATH=+(path)/data/service/hnp/bin` 是 **OHOS 适配版 conan 的专属语法**；
  在 job 实际调用的 conan 环境中该注入**未生效**（env.txt 的 PATH 里看不到）。
- 对照证据：同日同 profile 的 libuinputplus job cmake 却能执行成功——
  因为其**启动会话**（ssh 客户端侧组装的命令）自带了工具链 PATH。
  即：cmake 可达性取决于**启动 runner 的会话环境**，而非 conan 机制。

## 解法（r3 实测生效，编译 100%）

启动 runner 时显式前缀工具链 PATH（环境组装，不绕过锁，runner 照常排队）：

```sh
ssh <device> 'PATH=/data/service/hnp/bin:$PATH \
  sh ~/ohos-users/codex/<job>/run-conan-heavy.sh'
```

## 排查方法（对照法，10 分钟定位）

1. 看 run 目录 `logs/stdout.log`：失败是否恰在 `RUN: cmake` 行后。
2. 看 `logs/env.txt` 的 `PATH=`：是否含 `/data/service/hnp/bin`。
3. 设备上直接验证工具存在且可执行：
   `/data/service/hnp/bin/cmake --version`（HMDFS 上 `ls -la` 可能报
   Permission denied，但执行正常——元数据与执行权限表现不一致是已知怪癖，
   不要被 ls 的报错误导）。
4. 找一个**近期成功**的同类型 job，对比其 `logs/stdout.log` 里 cmake 是否
   执行过（`The C compiler identification is Clang 15.0.4`）与 `logs/env.txt`。

## 反模式（r1 实测误判，勿重复）

- **不要**把这个 127 归因到 `CMAKE_SYSTEM_NAME` 并试图用
  `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"` 之类配方改动去"修"
  （lasi/1.1.3 时代的 workaround）：删掉该别名后 127 依旧——两者无关。
- 适配版 conan（2.29.1 基线）会自动将 OHOS 映射为
  `CMAKE_SYSTEM_NAME=HarmonyOS` 并注入工具链环境；配方内手动别名反而
  覆盖其自动处理，属过时写法，可顺手删除，但它**治不了 127**。

## 证据（libsv 1.2，2026-09-27）

- r1/r2（无 PATH 前缀，配方有/无 Linux 别名各一轮）：均 cmake 127。
- r3 起（PATH 前缀）：`[100%] Built target test_*` 全部编译通过。
- 设备实测：`PATH=/data/service/hnp/bin:$PATH sh -c 'command -v cmake'`
  → `/data/service/hnp/bin/cmake`，`cmake version 4.1.2`。
