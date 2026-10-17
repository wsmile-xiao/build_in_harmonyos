# libbloom 2.0 适配笔记

## 编译环境

- 构建系统：makefile（GNU Make，无 configure）
- 编译日期：2026-09-14
- 编译器：clang/clang++（从 Conan conf 获取，R33）
- 状态：built（待真机预检通过后由 HMBS 提交）
- 上游：https://github.com/jvirkki/libbloom，tag v2.0（2022-09-18）
- 源码包：https://github.com/jvirkki/libbloom/archive/refs/tags/v2.0.tar.gz
- sha256：59965451ef033b0e060c9d7e472ead06af1ac61beddde11fe3ed4f5f4587bda6（本机 curl 下载后 certutil 实测）

## 上游结构

- `bloom.c` / `bloom.h`：过滤器主体（init/add/check/save/load/merge/free/reset/version）。
- `murmur2/MurmurHash2.c`：内嵌哈希实现，随主库一起编译进 `libbloom.a` / `libbloom.so`。
- `misc/test/test.c`：共享库测试（`make test` 构建为 `build/test-libbloom`），默认跑
  `basic()` + 6 组 `add_random`（含 100 万元素组），用 `/dev/urandom` 做输入。
- `misc/test/basic.c`：静态库冒烟测试（`make test` 构建为 `build/test-basic`）。
- `misc/test/perf.c` / `visualize.c`：性能与可视化工具，非测试，不接入。
- 上游 Makefile 无 `install` 目标，`package()` 手动拷贝。

## 编译步骤

```bash
make -C <source> CC=<conan-cc> AR=<conan-ar> RANLIB=<conan-ranlib> -j1
make -C <source> CC=<conan-cc> AR=<conan-ar> RANLIB=<conan-ranlib> -j1 test
```

产物：`build/libbloom.a`、`build/libbloom.so.2.0`（+ `libbloom.so.2` / `libbloom.so`
符号链接）。`package()` 拷贝 `bloom.h` 到 `include/`，库文件到 `lib/`，
`LICENSE` 到 `licenses/`，上游测试结果 JSON 到 `res/`（供 test_package 在
缓存命中轮重发证据）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `TOP := $(shell /bin/pwd)` 在 OHOS 上可能取空，导致 BINDIR 错误 | OHOS 无 `/bin/pwd`（/bin/sh 也可能缺失，见 ADAPTATION_GUIDE §8） | 补丁 `0001-makefile-posix-pwd.patch` 改用 `$(shell pwd)`，POSIX 兼容，无平台宏（PF5 安全） |
| 2 | 上游无 install 目标 | 上游 Makefile 只定义 all/test/clean | `package()` 用 Conan `copy()` 手动拷贝头文件与构建产物 |
| 3 | 交叉/CI 环境裸 `CC` 为空导致静默失败（R33） | release worker shell 环境变量不可靠 | 从 `tools.build:compiler_executables` 取 cc/ar/ranlib，显式传给 make |
| 4 | test_package 的 CMakeToolchain 嵌入 profile 编译器路径并 FORCE 覆盖，CLI `-D` 无法顶掉，真机报 `CMAKE_C_COMPILER` 缺失 | 工具链文件语义优先于命令行 | test_package 弃用 CMake，直接用回退后的 cc 编译单文件并直链 `libbloom.a`，不断言删减 |
| 5 | CI #46827 `add_random(10000, 0.0001, ...)` 报 `expected 0.0001 but observed 0.0002` (coll 2 vs 1)，真机曾通过 | 上游 `test.c` 每次从 `/dev/urandom` 取新随机数并断言观测误报率 `<=` 设计值；bloom 误报率是均值，n=10000/p=1e-4 时期望碰撞约 1 次，观测到 2 次属正常二项波动，非回归 | `test-basic`（确定性）仍跑一次；`test-libbloom`（随机输入）同一二进制最多重试 3 次，一次干净 exit 0 即通过。不放宽阈值、不跳过测试。 |

## 源码修改

- `patches/0001-makefile-posix-pwd.patch`：仅替换 `/bin/pwd` 为 `pwd`，一行实质改动，
  不碰构建逻辑，不引入 `__OHOS__` 宏。
- `/tmp` 只读适配：上游 `misc/test/test.c` 硬编码 `/tmp/libbloom.test` 与
  `/tmp/bloom.test`。原 `0002-tmpdir-for-tests.patch` 因 hunk 头行数与换行问题
  在真机 `apply_conandata_patches` 报 `Failed to parse patch`，改为
  `conanfile.source()` 内 Python 文本替换（插入 `libbloom_tmpdir()`  helper 并
  替换两处硬编码路径，语义不变），避免 unified-diff 脆弱性。

## 依赖版本

- 无第三方依赖；系统库 `m`（libm）在 `package_info()` 中声明为 system_libs。

## 验证结果

- 上游测试：`make test`（test-basic + test-libbloom），`HMBS_UPSTREAM_TEST_RESULT`
  标记 `discovered=2`，结果待真机预检回填。
- 消费者测试：`test_bloom`（basic/save_load/merge 共 3 例），
  `HMBS_TEST_PACKAGE_RESULT` 标记 `discovered=3`，结果待真机预检回填。
- 证伪计划（真机通过后补充）：确认参照输出非空；必要时用 `exit 1` 桩验证
  harness 能捕获失败；区分通过与静默跳过。

## 注意事项

- `make test` 中的 100 万元素组在真机上可能耗时较长，已设 subprocess 超时
  1200 秒；若超时将如实记录并考虑只跑 test-basic。
- test-libbloom 依赖 `/dev/urandom`；若 OHOS 真机缺失该设备文件，测试会
  明确报错（非静默跳过），届时按实际错误处理，不虚报通过。
- 本机 Windows 检出时 `archives/l/libXext` 与 `archives/l/libxext`
  因大小写不敏感冲突显示为本地修改，与本任务无关，未触碰。
