# srecord 1.65.0 适配笔记

## 编译环境

- 构建系统：CMake（要求 >= 3.22）
- 编译日期：2026-07-18
- OHOS 验证：SDK 6.1 + Conan 2.29.1（容器交叉编译）
- 主机历史验证编译器：Clang/Clang++ 18.1.3
- 状态：built（Conan 配方与 OHOS aarch64 构建通过；真机运行暂缓）

## 编译步骤

1. 使用 Homebrew 对齐源码 `srecord-1.65.0-Source.tar.gz`。
2. 应用 `patches/` 下七个补丁。
3. Conan：

```bash
conan create archives/s/srecord/1.65.0 \
  --user=ohpcd --channel=stable \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  --build=missing
```

等价 CMake 配置：

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DSRECORD_BUILD_DOCUMENTATION=OFF
cmake --build build
ctest --test-dir build --output-on-failure
cmake --install build
```

## 遇到的问题与解决方案

1. 初始化器将项目误判为 Autotools：源码仅含 CMakeLists.txt；按 CMake 适配。
2. 上游覆盖安装前缀为 `/usr`：仅在未显式指定前缀时设置默认值。
3. 文档目标强制依赖 Doxygen 等：增加 `SRECORD_BUILD_DOCUMENTATION`，OHOS 关闭。
4. 非 Windows 安装会收集主机运行库：限制为 Windows，避免打入主机 libc/libgcrypt。
5. CI 依赖：`libgcrypt/1.11.0` 已在 ohpcd；配方 `requires` 该包（传递 libgpg-error）。
6. x86_64 SDK 交叉主机上，双 OHOS profile 使 `cross_building()` 为 False，但动态 OHOS 二进制无法经 qemu-user 可靠执行：用 `platform.machine()` 检测 foreign aarch64，跳过本地 CTest，原生 CI 仍跑完整套件。
7. 原生 OHOS CI 上 CTest 出现 208/208 秒级失败：`test/test_prelude.sh` 硬编码 `testdir=/tmp/srecord-$$`，而鸿蒙 `/tmp` 为只读（E002）。改为使用 `$TMPDIR`，并将 `TMPDIR` 指到 build 目录内可写路径。
8. TMPDIR 修复后仍秒失败：`srec_*` 动态链 libgcrypt，而 OHOS 上 `conanrun` 常不注入 `LD_LIBRARY_PATH`（E019）。处理：链接时写入绝对 rpath；测试前显式设置 `LD_LIBRARY_PATH`；并把 `.so` 旁路到 build/`package/bin`；用 `ctest --output-on-failure` 直接跑（避开 `make test` 的 mkfifo）。
9. LD_LIBRARY_PATH 修复后仍 208/208 秒失败：shell-init/`pwd` 报 `getcwd: cannot access parent directories`（HMDFS）。`test_prelude.sh` 原逻辑 `here=$(pwd); test $? -eq 0 || exit 2` 直接退出。处理：prelude 优先使用 `SRECORD_TEST_HERE`/`PWD`；CMake 为每个测试注入绝对路径；`conanfile` 在跑 ctest 前 `chdir` 到 `build/test`。
10. CTest 跑出 206/208：`t0015a.sh` (maximum filter)、`t0016a.sh` (minimum filter) 报 `diff: Unknown option 'c'`。`test_prelude.sh` 的 diff 包装函数用 `which diff` 取 PATH 第一个 diff，OHOS 上 PATH 中 toybox `/usr/bin/diff` 排在前面，被捕获后 `diff -c` 不识别。处理：在 prelude 中先探测 `/data/service/hnp/bin/diff` 是否支持 `--strip-trailing-cr` + `-c`，是则用它，否则退回 PATH 中的 diff。
11. `conan create` 上游 CTest 208/208 后 `test_package/smoke_test.sh` 失败：`bin/srec_*` 报 `Operation not permitted`（E077）。`cmake.install`/RPATH 改写会使 `.codesign` 失效或缺失。处理：`package()` 对三个 CLI 及旁路 `.so` 做 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`；`test_package` 执行 smoke 前再兜底重签。

## 源码修改

- `0001-CMakeLists.txt.patch`：安装前缀修复、文档开关。
- `0002-etc-configure.cmake.patch`：文档关闭时不查找 Doxygen/Graphviz。
- `0003-etc-packaging.cmake.patch`：运行时依赖收集限 Windows。
- `0004-srecord-CMakeLists.txt.patch`：文档关闭时不安装 Doxygen 产物。
- `0005-test-test_prelude.sh.patch`：CTest 临时目录改用 TMPDIR（E002）；getcwd 失败时回退到绝对路径。
- `0006-test-CMakeLists.txt.patch`：为 CTest 注入 `PWD`/`SRECORD_TEST_HERE` 并固定 WORKING_DIRECTORY。
- `0007-test-test_prelude.sh.patch`：在 prelude 中优先选用支持 `--strip-trailing-cr` + `-c` 的 GNU diff，回退到 PATH 中的 diff。

## 依赖版本

- cmake >= 3.22
- libgcrypt/1.11.0（Conan / ohpcd）
- libgpg-error/1.55（传递依赖）

## 验证结果

- OHOS aarch64 `conan create` 上游 CTest：208/208 通过（100%）。
- 主机侧官方 CTest：208/208 通过（历史验证）。
- 三个命令产物已安装到包 `bin/`。
- `commands.json`、`test_package/MANIFEST.yml` 已就绪。
- 上游测试失败用例 `t0015a.sh` / `t0016a.sh`（`diff -c` 误用 toybox diff）已由 `0007-test-test_prelude.sh.patch` 修复；见 `manifest.yaml` 的 `test_results`。

## 注意事项

- OHOS 设备执行 `bin/srec_*` 需要 ELF 签名（E077/E082）。`package()` 在 install 后对 `srec_cat`/`srec_cmp`/`srec_info` 及旁路 `.so` 调用 `binary-sign-tool -selfSign 1`；`test_package` 在跑 `smoke_test.sh` 前再兜底重签。
- 未做 OHOS 真机预编译包部署验证时保持 `status: built`；原生 CI 完整 `conan create`（含 test_package）通过后可改为 `published`。

---

**编译结束**: 2026-07-24
**最终状态**: built（上游 208/208 全通过；test_package 经 ELF 签名后应可通过 smoke_test）
