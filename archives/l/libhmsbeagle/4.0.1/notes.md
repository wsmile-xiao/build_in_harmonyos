# libhmsbeagle 4.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15 (HarmonyOS PC aarch64)
- 状态: built (待真机预检)

## 上游信息
- 上游仓库: https://github.com/beagle-dev/beagle-lib
- 上游版本: v4.0.1 (BEAGLE v4.0.1, 2023-10-13, Bug fixes: patch ARM64 on linux)
- 源码包: https://github.com/beagle-dev/beagle-lib/archive/refs/tags/v4.0.1.tar.gz
- sha256: 9d258cd9bedd86d7c28b91587acd1132f4e01d4f095c657ad4dc93bd83d4f120 (实测下载 4080874 字节)
- 许可证: MIT
- 包名说明: 顶层 CMake `BEAGLE_PACKAGE_NAME=libhmsbeagle`, 版本 4.0.1; 本配方打包 `hmsbeagle` 主库 + `hmsbeagle-cpu` CPU 插件。

## 编译步骤

CMake 配置 (OHOS aarch64, CPU-only):
```bash
cmake -DBUILD_SHARED_LIBS=ON \
  -DBUILD_CUDA=OFF -DBUILD_OPENCL=OFF -DBUILD_JNI=OFF -DBUILD_SSE=OFF \
  -DBEAGLE_OPTIMIZE_FOR_NATIVE_ARCH=OFF \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  <source>
cmake --build . --config Release
ctest --output-on-failure
```
Note: BUILD_SHARED_LIBS must stay ON. Plugin system dlopens
libhmsbeagle-cpu.so.40.0.0 at runtime (UnixSharedLibrary.h +
Plugin.cpp findPlugin). Static .a can never be loaded.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层默认 `-march=native` | `set(BEAGLE_OPTIMIZE_FOR_NATIVE_ARCH true)` 强制注入 `-march=native`, 在 OHOS aarch64 上不可移植 | 补丁改为 `false`, 配方再传 `-DBEAGLE_OPTIMIZE_FOR_NATIVE_ARCH=OFF` 双保险 |
| 2 | plugin dlopen needs shared .so | UnixSharedLibrary.h dlopens libhmsbeagle-cpu.so.40.0.0; static .a fails with NO_RESOURCE in 0.03s | keep upstream add_library SHARED, force BUILD_SHARED_LIBS=ON, default shared=True |
| 3 | JNI 在无 JDK 环境 FATAL | `find_package(JNI)` + `BUILD_JNI=ON` 默认, OHOS 真机无 JDK 会直接 FATAL | 配方强制 `BUILD_JNI=OFF` |
| 4 | CUDA/OpenCL 在 OHOS 无运行时 | OHOS 无 NVIDIA CUDA 与 OpenCL SDK, `find_package(CUDA/OpenCL)` 无意义 | 配方强制 `BUILD_CUDA=OFF`, `BUILD_OPENCL=OFF` |
| 5 | SSE 是 x86 专用 | `BeagleCPUSSE*` 用 x86 intrinsics, aarch64 编译失败 | 配方强制 `BUILD_SSE=OFF` |
| 6 | 头文件安装路径特殊 | 安装到 `include/libhmsbeagle-1/libhmsbeagle/beagle.h` | `package_info.includedirs=["include","include/libhmsbeagle-1"]`, 测试用 `#include <libhmsbeagle/beagle.h>` |
| 7 | 构建树 ctest 0.06s 失败, 上一轮切 shared/useSSE 后仍复现 | 上一方案无效的原因: shared+VECTOR_NONE 只是必要条件, 非充分条件。`UnixSharedLibrary.h` 用裸 soname `libhmsbeagle-cpu.so.40.0.0` 做 `dlopen` (无目录), 构建树产物在 `libhmsbeagle/CPU/` 下, 不在 loader 默认搜索路径, `cmake.test()` 在 `cmake.install()` 之前运行必然 `Unable to load CPU plugin!` + `NO_RESOURCE`。故换路线: `build()` 在 ctest 前 walk `build_folder` 收集含 `libhmsbeagle*.so` 与 `hmctest` 的目录, 注入 `LD_LIBRARY_PATH` 后再 `cmake.test()`; 不改测试断言。test_package 第二次直调二进制同样补 package `lib` 的 `LD_LIBRARY_PATH`。 |
| 8 | 纯 LD_LIBRARY_PATH 仍 0.06s 失败 (2026-09-19 12:15 轮) | 前次仅设环境变量未改变结果, 说明需不同机制+可见诊断。本轮改走文件就位+诊断路线: 把构建树 `libhmsbeagle*.so*` 复制到 `hmctest` 同目录 (binary-dir/cwd 可解析), 保留 LD_LIBRARY_PATH, 失败时在日志尾部打印 `LastTest.log` 尾段、插件文件列表与直调 `hmctest` 的 rc+输出, 下轮据真实 stderr 定因, 不改断言。 |
| 9 | 文件复制+环境仍 0.06s, LastTest 显示空资源列表 (2026-09-19 12:41 轮) | 前两轮 (纯环境、复制到二进制目录) 指纹相同且 LastTest 证实 `Available resources:` 为空后 `Failed to obtain BEAGLE instance`, 说明裸 soname 搜索在 OHOS 构建树根本不可达。本轮改走源码兜底路线: 给 `UnixSharedLibrary.h` 加显式斜杠路径重试 (依次试 `BEAGLE_PLUGIN_DIR`、`LD_LIBRARY_PATH` 各目录+`/`+soname 及 `./`+soname, 直接 open 文件), `build()` 仅负责把构建树 CPU 插件目录同时写入这两个变量; 复制文件机制已移除, 不改断言。 |
| 10 | 源码兜底+环境仍 0.06s 空资源列表 (2026-09-19 13:13 轮) | 上轮教训: 单一路线的环境变量可能到不了 ctest 子进程, 而 `./`+soname 重试要求插件文件真实落在 ctest cwd (二进制同目录)——但复制机制已被移除, 所以两个兜底同时落空。本轮组合路线: (1) `UnixSharedLibrary.h` 补丁保留并增强——新增 `<exe-dir>`+soname 重试 (经 `/proc/self/exe` 定位, 不依赖 cwd/环境) 与每次 `dlopen` 尝试的 `dlerror` 打到 stderr (下轮可直接看到是“文件不存在”还是“依赖缺失”); (2) `build()` 恢复并固化文件就位——把构建树 `libhmsbeagle*.so*` (按 basename, 解析版本软链到实体字节) 复制到每个 `hmctest` 二进制同目录, 同时保留 `LD_LIBRARY_PATH`/`BEAGLE_PLUGIN_DIR` 注入。不改任何测试断言与数值。 |
| 11 | 组合路线仍失败但拿到决定性诊断 (2026-09-19 13:29 轮) | 上轮补丁已证实生效: 真机日志出现 `BEAGLE: dlopen ...` 逐次尝试行, `<exe-dir>` 回退正确定位到 `build/Release/examples/`, 可选插件 (avx/openmp/sse/cuda) 报 `No such file` 属预期 (BUILD_*=OFF 未构建)。但主 CPU 插件的尝试行落在摘要截断区, 仍无法判定是“文件不在”还是“依赖缺失”。本轮换策略: (1) 釜底抽薪——`dlopen` 由 `libhmsbeagle.so` 内部发起, 给它加相对 RUNPATH (`BUILD_RPATH $ORIGIN/CPU`, `INSTALL_RPATH $ORIGIN`), loader 无需任何环境变量/复制即可解析裸 soname (glibc/musl 均支持 `$ORIGIN`, 官方 CI 无感); (2) 诊断收敛——直调 `hmctest` 只打印主 CPU 插件行 (过滤 avx/openmp/sse/cuda/opencl)、二进制目录文件清单与当时环境变量, 体积可控必进日志尾。不改任何测试断言与数值。 |
| 12 | 2026-09-20 preflight: github timeout once then retry OK + ctest hmctest NO_RESOURCE (empty resources) | download: single URL has no fallback, transient ConnectTimeout to github.com stalls source(); ctest: prior RUNPATH relied on fragile CMakeLists string anchor. | (1) conandata url -> ordered list [gh-proxy.com mirror, official URL] per ci/conan/build_and_test.sh, sha256 unchanged; (2) RUNPATH via CMakeToolchain CMAKE_BUILD_RPATH=$ORIGIN/CPU:$ORIGIN + CMAKE_INSTALL_RPATH=$ORIGIN (replaces anchor patch, keeps UnixSharedLibrary patch + staging + env); (3) MANIFEST adds upstream_test_total=1 + ctest_entries. |
| 13 | 2026-09-20 preflight(2nd): download OK but hmctest still 0.05s NO_RESOURCE; tail only shows optional openmp noise | prior cmake.test()+os.environ chain may sanitize env before reaching hmctest child; decisive plain-cpu lines hidden by truncation. | (1) keep mirror/RPATH/patch/staging; (2) NEW: run `ctest --output-on-failure` directly via subprocess with explicit env+cwd instead of cmake.test(); (3) add compact tail probes: BEAGLE_PLAIN existence+size for libhmsbeagle-cpu.so.40.0.0 in cpu/exe/LD dirs + BEAGLE_RUNPATH from readelf -d libhmsbeagle.so. |
| 14 | 2026-09-20 preflight(3rd): direct-ctest still rc=8 empty resources; tail still only avx/openmp noise | Prior round invalid because: explicit env/cwd fixes the DELIVERY path, but if the built file NAME differs from the dlopened bare soname (CMake SOVERSION handling on unknown HarmonyOS platform may emit .so.40 / .so instead of .so.40.0.0), every path/env/RUNPATH trick fails with the same NO_RESOURCE fingerprint. Upstream issue #156 (ARM Raspbian, no-SSE, same empty-resources symptom, open) supports an ARM-only build-tree cause distinct from loader search paths. | NEW filename route (keeps all prior infra): (1) emit BEAGLE_PLUGIN_LS listing of every libhmsbeagle*.so* with size+symlink target for evidence; (2) if libhmsbeagle-cpu.so.40.0.0 absent but another libhmsbeagle-cpu*.so* variant exists, copy real bytes to the expected soname in plugin dirs + each hmctest dir (BEAGLE_SONAME_FIX lines); no assertions touched. |

## 上游测试清点
- `examples/CMakeLists.txt` 注册 `add_test(hmctest hmctest)` (1 个 ctest 用例, 另有 `synthetictest` 可执行文件但未注册为 ctest)。
- `tests/run_tests.sh` 是 shell 驱动的基准对比脚本 (需 BEAST/R 数据, 非 ctest, 不纳入本次通过率)。
- 配方 `build()` 在 `can_run` 时执行 `cmake.test()` 即 `ctest --output-on-failure`, 真机证据待预检回填。
- 2026-09-19 round2 re-diagnosis: useSSE=false alone still failed 0.03s, so SSE flag was NOT the sole cause. New evidence: beagle.cpp beagleLoadPlugins()+Plugin.cpp findPlugin() dlopen libhmsbeagle-cpu.so.40.0.0 (see UnixSharedLibrary.h); previous round stripped SHARED -> static .a -> dlopen always fails -> empty resource list -> beagleCreateInstance NO_RESOURCE. Different route: revert SHARED stripping, force BUILD_SHARED_LIBS=ON, default shared=True. useSSE=false kept (still needed for VECTOR_NONE on aarch64 CPU-only).
- 机器证据: `build()` 在真实 ctest 运行后输出 `HMBS_UPSTREAM_TEST_RESULT` (discovered=1/executed=1, passed/failed 取自 ctest 实际退出码); `test_package/test()` 运行消费者二进制并计数 `CHECK-OK:` 行输出 `HMBS_TEST_PACKAGE_RESULT` (discovered=3/passedCount=实测), 同时重发上游标记以穿越 conan 缓存命中轮。
- 防证伪: `hmctest` 会计算 3-taxon 似然并校验数值, 非空输出; 若被测库替换为 `exit 1` 桩, ctest 必失败, 不存在静默通过。消费者侧仅退出码 0 不算通过, 必须同时数出 3 行 `CHECK-OK:`。

## 依赖版本
- 无外部依赖 (CPU-only 构建仅需系统 `m/dl/pthread`)。

## 验证结果
- 待 HMBS 真机预检 (conan create + ctest + test_package)。
- 本地 Windows 仅完成配方静态检查, 未运行 conan (按规范不在本机运行 conan)。

## 注意事项
- 本库非系统同名库 (`/lib` 无 libhmsbeagle), 保持共享库 (plugin dlopen 要求), 保留 `shared` 选项但默认 True 且强制 BUILD_SHARED_LIBS=ON。
- Java 绑定 (JNI) 与 GPU 插件不在本次适配范围, 已在补充说明声明。
