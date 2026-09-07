# hopscotch 0.1.2 适配笔记

## 状态与来源
- 状态：`built`（native/Conan 构建和真实 Conan consumer 已通过；上游 test target 因发行包缺失外部测试头未执行；未标记 `published`）。
- 构建系统：上游 raw Makefile；语言：C99；许可证：MIT。
- 源码 URL 与 SHA256：`https://github.com/silentbicycle/hopscotch/archive/refs/tags/v0.1.2.tar.gz` / `5f62bcb4650e897d7b786ea95c218af5a0cd64e4e344f60378cc5f8cfd8569cd`。

## 配方与安全解包
- `source()` 使用安全的 Python `tarfile` 遍历，拒绝越界路径并跳过符号链接；上游 `vendor/greatest.h` 是断裂的绝对链接，不能在 HMDFS 上跟随。
- `build()` 在 source folder 执行显式 `CC/AR/RANLIB` 的 `make -j1`；`package()` 提供 `include/hopscotch.h`、`lib/libhopscotch.a` 和 `bin/hopscotch`。
- 无上游 patch；recipe 仍显式调用 `apply_conandata_patches()`/`export_conandata_patches()` 以满足 Conan 配方门禁。

## 验证
最终 Conan 命令使用 host/build `ci/conan/profiles/ohos-aarch64`，并显式覆盖 `compiler.cppstd=17`、`compiler.libcxx=libc++`、`os.version=6.0`、`tools.build:jobs=1`。Conan clean create 成功，test_package 通过 CTest 编译并运行真实 API consumer，调用 `hopscotch_new`、`hopscotch_add`、`hopscotch_seal`、`hopscotch_solve`、`hopscotch_free`：`TOTAL=1 PASS=1 FAIL=0 SKIP=0 NOT_RUN=0`（测试 target 统计）。

上游 `make test` 的唯一 test target 统计为 `TOTAL=1 PASS=0 FAIL=0 SKIP=0 NOT_RUN=1`：编译阶段首先报 `fatal error: 'greatest.h' file not found`，该发行包还需要外部 `greatest`/`theft`，当前设备没有这些测试依赖。该项未写成 PASS；Conan C API consumer 是替代验证，不能替代未覆盖的 property/benchmark 测试。
