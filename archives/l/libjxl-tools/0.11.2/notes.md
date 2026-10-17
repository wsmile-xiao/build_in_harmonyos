# libjxl-tools 0.11.2 适配笔记（返修轮）

JPEG XL 参考实现命令行工具集（`cjxl` 编码器 / `djxl` 解码器 / `jxlinfo` 容器信息查看器）
的 HarmonyOS PC (arm64 / OHOS) Conan 2.x 适配。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-25（返修）
- 编译器: clang / clang++（OHOS SDK 15，target `aarch64-unknown-linux-ohos`）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8,
  compiler=clang 15, compiler.libcxx=libc++, compiler.cppstd=17, build_type=Release）
- 构建并发: `CONAN_CPU_COUNT=2`（-j2，防 OOM）
- 状态: built（conan create + conan-verify 通过，未 upload）

## 编译步骤

1. `CONAN_CPU_COUNT=2 conan create archives/l/libjxl-tools/0.11.2 -pr:h=<profile> -pr:b=<profile> --build=missing`
2. `source()`：下载 libjxl 0.11.2 官方 tarball，并把 skcms 单独下载解压到 `third_party/skcms`
   （发布 tarball 不含 git 子模块）。
3. `generate()`：`CMakeToolchain` 注入约 25 个 `-DJPEGXL_*`/`-DBUILD_*` 变量，关闭不需要的
   编解码器/jpegli/benchmark/examples，开启 `JPEGXL_ENABLE_TOOLS=ON` + `JPEGXL_ENABLE_SKCMS=ON`；
   OHOS 下设置 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`、
   `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`；RPATH 设为 `$ORIGIN/../lib`；
   通过缓存变量把 Conan 的 brotli/highway/**libpng/zlib** 包路径喂给 libjxl 的
   `FindBrotli.cmake`/`FindHWY.cmake` 以及 CMake 模块 `FindPNG`/`FindZLIB`。
4. `build()`：`apply_conandata_patches()`（无补丁）+ `cmake.configure()` + `cmake.build()`。
5. `package()`：`cmake.install()` 安装 `bin/{cjxl,djxl,jxlinfo}`、`lib/*.a`、`include/jxl/*`；
   复制 LICENSE；把 brotli、**libpng16** 的 `.so*` 复制进包内 `lib/`；从 Conan 静态 `libz.a`
   **合成 `libz.so`**（SONAME `libz.so`）随包分发；对 `bin/` 可执行与 `lib/` 运行时 `.so`
   统一 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 自签名。
6. `conan create` 末尾自动运行 `test_package/`（真实往返 + **空环境往返**）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-j16` 构建被 OOM 杀死 | 编译机空闲内存仅 ~1GB，libjxl 单文件（highway 模板）编译占用高 | 构建设 `CONAN_CPU_COUNT=2`（-j2），通过 |
| 2 | `JPEGXL_STATIC=ON` 链接失败 | 该选项向 `EXE_LINKER_FLAGS` 追加 `-static`，强制所有传递依赖静态；brotli 配方只产 `.so`，lld 拒绝 | 改为 `BUILD_SHARED_LIBS=OFF`（内建 libjxl 静态）+ `JPEGXL_STATIC=OFF`，brotli 保持动态 |
| 3 | 工具运行时找不到 brotli `.so` | brotli 为动态依赖，鸿蒙 `$ORIGIN/../lib` 需显式烘焙 | `package()` 复制 brotli `.so*` 进包 `lib/`；`CMAKE_INSTALL_RPATH=$ORIGIN/../lib` |
| 4 | 发布 tarball 无 skcms → 只能依赖未发布的 lcms2 | GitHub release tarball 不含 git 子模块 | `source()` 按上游锁定 commit 下载 skcms 到 `third_party/skcms`，`JPEGXL_ENABLE_SKCMS=ON` |
| 5 | OHOS clang 下 CMake 平台探测失败（E092） | CMake 不认识 `harmonyos/ohos` 目标平台 | `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` |
| 6 | conan-verify G1 报 "缺少 export_sources() / 补丁应用调用" | 配方用 `exports_sources="patches/*"` 属性 | 改为 `def export_sources()` + `build()` 内 `apply_conandata_patches()` |
| 7 | conan-verify G1 报 "test_package/MANIFEST.yml 缺失" | 缺 CI L0e 门禁要求的测试声明文件 | 新增 `test_package/MANIFEST.yml` |
| **8** | **旧包干净环境运行报 `Error loading shared library libpng16.so.16` / `symbol not found`（验收不通过）** | **libjxl extras 的 PNG 编解码无条件启用（`JPEGXL_BUNDLE_LIBPNG=OFF` → `find_package(PNG)`），但配方未声明 libpng；`Found PNG/ZLIB` 从宿主 `/storage/.../usr/local` 偶合到 libpng 1.6.43/libz 1.3.1，包内 `lib/` 未随附 → 不自包含** | **`requires("libpng/1.6.58")`（+ 显式 `zlib/1.3.1.1`）；`generate()` 注入 `PNG_PNG_INCLUDE_DIR`/`PNG_LIBRARY`/`ZLIB_INCLUDE_DIR`/`ZLIB_LIBRARY` 使 `Found PNG/ZLIB` 指向 Conan 包；`package()` 随包 `libpng16.so*` 并合成/随包 `libz.so`** |
| **9** | **旧 test_package 掩蔽了缺陷** | **test_package 用 `env="conanrun"`（含宿主 `LD_LIBRARY_PATH`）运行，即使不自包含也“通过”** | **test_package 新增 `env={}` 空环境往返断言，`Found PNG` 验证 + `env -i` 人工验收共同兜底** |
| **10** | **`self.dependencies["zlib"].package_folder` 取到 `None`** | **Conan 2 对“纯传递依赖”不填充 consumer recipe 的 `package_folder`** | **将 `zlib/1.3.1.1` 提升为直接 requires（与 libpng 同版本 → 同一图节点，无冲突）** |
| **11** | **ohpcd 的本机缓存存在多个旧 `libpng/1.6.58` revision，最新者 requires `zlib/1.3.1.1.1.1`，与 ohpcd 发布的 `zlib/1.3.1.1` 冲突** | **本机缓存被既有构建轮次污染（非发布态）；CI 干净 worker 只会取到 ohpcd 的 `libpng/1.6.58#d25df07`（requires `zlib/1.3.1.1`）** | **本机 `conan remove libpng/1.6.58 -c` 后重新 `conan download` 以对齐 CI；配方引用 `zlib/1.3.1.1` 与 ohpcd 发布态一致** |

## 源码修改

无。未修改任何上游源文件，`patches/` 为空，`patches_applied: []`。

## 依赖版本

| 依赖 | 版本 | 类型 | 运行时分发 |
|------|------|------|-----------|
| `brotli` | 1.2.0 | 共享 | 随包 `lib/libbrotli*.so*` |
| `highway` | 1.3.0.2 | 静态 | 链入内建 libjxl |
| `libpng` | 1.6.58 | 共享（ohpcd 默认 shared=True） | 随包 `lib/libpng16.so*` |
| `zlib` | 1.3.1.1 | 静态（ohpcd 仅 `libz.a`） | 链入 cjxl/djxl；并由 `libz.a` 合成 `lib/libz.so` 供 `libpng16.so.16` 运行时 |
| skcms（内置） | commit `b2e692629c1fb19342517d7fb61f1cf83d075492` | 源码 | 链入内建 libjxl |
| `gtest` | 1.17.0 | 仅上游测试构建 | 非包依赖 |

> 系统运行时（不随包）：`libc.so`、`libc++_shared.so`（`/system/lib64`，在 `ld-musl-aarch64.path` 搜索路径内）。

## 验证结果

```bash
# conan create（CONAN_CPU_COUNT=2 防 OOM）
CONAN_CPU_COUNT=2 conan create archives/l/libjxl-tools/0.11.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# 配方 revision: cb0fffde4cc646b453bd0419ce15371c
# 包 ID:        a8c57f366e0313c323f14358e52e86babaec949e
# 包 revision:  806f2c5802585f71d62dd6410d544c51
# 包路径:       /storage/Users/currentUser/.conan2/p/b/libjx327376a5a1e24/p

# conan-verify（G0-G4 + L2/L4/L5）
CONAN_CPU_COUNT=2 python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libjxl-tools 0.11.2 --project-dir <worktree>
# → ✅ 配方验证通过: libjxl-tools 0.11.2（G4 脚本缺陷 → L2/L4/L5 人工补跑，见 reports/l2-l4-l5-manual.md）

# 构建日志 Found PNG/ZLIB（已指向 Conan 包）
# -- Found ZLIB: .../.conan2/p/zlibef5df15a693be/p/lib/libz.a (found version "1.3.1")
# -- Found PNG:  .../.conan2/p/libpne65b0a3aa7f9b/p/lib/libpng16.so (found version "1.6.58")

# ⭐ 干净环境验收（env -i，无 LD_LIBRARY_PATH）
env -i <pkg>/bin/cjxl --version     # cjxl v0.11.2 503c4c2c9 [NEON_WITHOUT_AES]   rc=0
env -i <pkg>/bin/djxl --version     # djxl v0.11.2 503c4c2c9 [NEON_WITHOUT_AES]   rc=0
env -i <pkg>/bin/jxlinfo --help     # Usage: ...                                    rc=0
env -i <pkg>/bin/cjxl in.ppm out.jxl    # rc=0，out.jxl 72 B
env -i <pkg>/bin/djxl out.jxl out.ppm   # rc=0，out.ppm 59 B
env -i <pkg>/bin/jxlinfo out.jxl        # JPEG XL image, 4x4, lossy, 8-bit RGB   rc=0

# DT_NEEDED（新包 bin/cjxl）：libbrotli{dec,common,enc}.so.1 + libpng16.so.16（包内） + libc++_shared.so + libc.so
# 旧包额外含 libz.so 与“包内缺失的 libpng16.so.16”——已消除宿主偶合。
```

test_package（`conan create` 内自动执行）：

```
cjxl --version / djxl --version  OK
cjxl in.ppm out.jxl → djxl out.jxl out.ppm → jxlinfo out.jxl  OK
clean-env (env={}) roundtrip OK — package is self-contained
libjxl-tools 0.11.2 roundtrip: cjxl encode, djxl decode, jxlinfo inspect — OK
```

详见 `reports/verification.md`、`reports/l2-l4-l5-manual.md`、`reports/conan-create.log`。

## 上游测试（gtest / ctest）

在**独立临时构建目录**开启 `BUILD_TESTING=ON` + `JPEGXL_FORCE_SYSTEM_GTEST=ON`（gtest/1.17.0）
构建并运行，不触碰成品包。完整命令、逐二进制明细与原始日志摘录见 `reports/upstream-tests.md`。
本轮仅改动 `generate()`（新增 PNG/ZLIB 缓存变量与依赖声明）与 `package()`（随包 .so），
不改变上游测试构建配置，结论不变。

| 指标 | 数值 |
|------|------|
| 测试二进制总数 | 62 |
| 上游定义 gtest 用例总数 | **4782** |
| 通过（`[ OK ]`） | **4778** |
| gtest 断言失败（`[ FAILED ]`） | **0** |
| 通过率 | **99.92%**（4778/4782） |
| 未执行 | 2（`splines_test`：读上游 `main` 分支不存在的 `jxl/splines.pfm` 崩溃） |
| SKIPPED / DISABLED | 1（`gauss_blur_test`）/ 1（`jxl_test`，均为上游行为） |

**结论**：**0 个 gtest 断言失败，通过率 99.92%**。发布 tarball 不含 `testdata/` 子模块导致
测试读取样例数据时 `SIGTRAP`；本轮已通过 CI 既有 GitHub 代理镜像 `gh-proxy.com`
取回 `libjxl/testdata`（284 文件 / 约 112 MiB，非 git-lfs）并放到编译期宏
`-DTEST_DATA_PATH=<conan source>/testdata` 指向的路径，使全量用例可执行。
唯一无法执行的 `splines_test.SplinesTest.Drawing` 所需 `jxl/splines.pfm`
在上游 `libjxl/testdata@main` 中不存在（API 404），属上游测试数据缺失。
未修改任何上游测试源码；仅独立测试构建做了两处 CMake 配置调整
（`JPEGXL_ENABLE_FUZZERS=OFF`、`CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST`），
详见 `reports/upstream-tests.md`。

## 适配完整性（R40）

libjxl-tools 属多媒体/编解码类，按 R40 说明适配完整性评估如下：

- **无平台相关编解码后端需适配**：上游 libjxl 为纯软件 JPEG XL 编解码实现，不含
  GPU/硬件加速后端，也不访问摄像头/蓝牙等外设 HAL，因此不存在需要鸿蒙化改写的
  设备接口代码。适配点集中在构建与运行时：
  CMake 平台探测（`CMAKE_SYSTEM_NAME`，知识库 E092）、依赖钉扎
  （FindPNG/FindZLIB → Conan 包）、自包含 RPATH（`$ORIGIN/../lib`）与二进制签名。
- **实质性功能验证**：`test_package` 执行真实编解码往返（PPM → `cjxl` → `.jxl` →
  `djxl` → PPM，并用 `jxlinfo` 读取容器），覆盖 brotli + libjxl + skcms 真实管线，
  非仅 `--version()`；并额外以 `env={}` 空环境断言包自包含（不依赖宿主
  `LD_LIBRARY_PATH`）。
- **上游测试**：62 个 gtest 二进制 / 4782 用例，4778 通过（99.92%），0 断言失败。

结论：本适配无 stub/占位式平台分支，无未适配的平台功能；建议人工确认。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/cjxl` | JPEG XL 编码器（已签名） |
| `bin/djxl` | JPEG XL 解码器（已签名） |
| `bin/jxlinfo` | JPEG XL 容器信息查看器（已签名） |
| `lib/*.a` | 内建 libjxl / jxl_cms / jxl_threads / jxl_extras_codec 静态库 |
| `lib/libbrotli*.so*` | brotli 运行时库（随包自包含） |
| `lib/libpng16.so*` | libpng 运行时库（随包自包含，`NEEDED libz.so`） |
| `lib/libz.so` | 由 Conan 静态 `libz.a` 合成的共享 zlib（随包自包含） |
| `include/jxl/*.h` | libjxl 公共头文件 |

## 注意事项

1. **签名工具硬编码路径**：`_sign_binaries()` 使用 `/data/service/hnp/bin/llvm-objcopy` 与
   `/data/service/hnp/bin/binary-sign-tool`（本仓库 CLI 工具配方既有核准做法）。
2. **CMAKE_SYSTEM_NAME=Linux**：`generate()` 在 `settings.os == "OHOS"` 时覆盖为 `Linux`
   （同已发布 `highway/1.3.0.2` 配方做法，绕过 E092）。
3. **conan-verify G4 脚本缺陷**：G4 解析 `conan list --format=json` 用两层索引，conan 2.29
   返回单层完整引用键，取包 ID 失败 → L2/L4/L5 被跳过。已人工补跑
   （`reports/l2-l4-l5-manual.md`）。`scripts/` 只读，未改。
4. **libz.so 为合成产物**：ohpcd 的 zlib 包纯静态（仅 `libz.a`），而 Conan `libpng16.so.16`
   携带 `NEEDED libz.so`，OHOS 默认搜索路径无 `libz.so`（`/usr/lib` 只有 SONAME 不匹配的
   `libz.so.1`），故由 `clang -shared` 从 `libz.a` 合成 `SONAME=libz.so` 的共享库随包分发。
5. **上游 testdata 缺失**：libjxl 发布 tarball 不含 `testdata/` 子模块，依赖测试数据的用例失败——
   属上游打包限制，非适配缺陷。
6. **本机缓存预清理**：本机 conan 缓存曾残留多个旧 `libpng/1.6.58` revision（最新者 requires
   `zlib/1.3.1.1.1.1`），会与 ohpcd 发布态（`zlib/1.3.1.1`）冲突。已 `conan remove libpng/1.6.58 -c`
   后重新 `conan download` 以对齐 CI；配方本身引用 ohpcd 发布态版本，无需本机干预即可在 CI 复现。
