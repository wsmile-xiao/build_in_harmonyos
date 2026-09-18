# libcerfcpp 3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (HarmonyOS PC aarch64, conan profile ci/conan/profiles/ohos-aarch64)
- 状态: built (待真机预检通过后由 HMBS 统一提交)

## 上游信息
- 上游仓库: https://jugit.fz-juelich.de/mlz/libcerf
- 上游版本: v3.3 (2025-10-25 发布)
- 源码包: https://jugit.fz-juelich.de/mlz/libcerf/-/archive/v3.3/libcerf-v3.3.tar.gz
- sha256: 7cbece26ad94bd375eb81fee2b540d0ef68bbeb0994358e57bd588173f96b8ec
  (2026-09-17 直连官方 URL 两次下载均得此值，与真机 source() 计算值一致；GitLab 动态归档，顶层目录含提交 7e6b6370，解包 90 文件正常)
- 许可证: MIT
- 本包含义: libcerf 源码树中的 C++ 接口库 libcerfcpp (与 Alpine/Fedora/MSYS2 的拆包口径一致)

## 编译步骤

上游为 CMake 项目 (cmake_minimum_required 3.20)，配方关键配置:
```cmake
-D BUILD_SHARED_LIBS=OFF (默认静态, shared=True 时为 ON)
-D CERF_C=OFF
-D CERF_CPP=ON
-D LIB_MAN=OFF
-D LIB_RUN=OFF
-D BUILD_TESTING=ON
-D CMAKE_POLICY_VERSION_MINIMUM=3.5
```

构建流程 (conanfile.py):
1. `get()` 解包上游源码
2. `CMakeToolchain` 生成工具链
3. `cmake.configure()` + `cmake.build()` 编译 libcerfcpp
4. `_run_upstream_tests()` 在真机执行 `ctest --output-on-failure`，
   解析汇总行 `N% tests passed, M tests failed out of K` 得到真实计数，
   输出 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `build_folder/hmbs_upstream.json`
5. `cmake.install()` 安装头文件/库/CMake 配置
6. `package()` 把 `hmbs_upstream.json` 复制进包内 `res/`，供 test_package
   在缓存命中轮次复发证据

test_package 流程:
1. CMake 构建 `test_cerfcpp` 并链接 `cerf::cerfcpp`
2. `ctest` 运行消费者测试
3. 直接执行 `./test_cerfcpp`，统计 `CHECK-OK:` 行数 (要求 6/6)，
   输出 `HMBS_TEST_PACKAGE_RESULT`
4. 读取 `<package>/res/hmbs_upstream.json` 复发 `HMBS_UPSTREAM_TEST_RESULT`

## 上游测试清点

- 来源: 上游 `test/` 目录 + `testcpp/CMakeLists.txt` (file GLOB test/*test.c，
  每个编译为 `%_cpp` 可执行文件并 `add_test`)
- C++ 侧共 9 个 ctest 用例: cerftest_cpp, dawsontest_cpp, erfcxtest_cpp,
  imwofxtest_cpp, realtest_cpp, statusquotest_cpp, voigttest_cpp,
  widthtest_cpp, wofztest_cpp
- (源码树另有 9 个 `_c` 测试，属于 C 库 libcerf，本包 CERF_C=OFF 不构建)
- 参考证据: Alpine Linux libcerf 3.3 构建日志显示 18/18 通过
  (其中 9 个 `_cpp` 即本包套件)；Fedora/MSYS2 亦从同一源码同时产出
  libcerf 与 libcerfcpp
- 通过率数字以真机预检 `conan create` 日志为准，见 PR 正文

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 包名 libcerfcpp 与源码包名 libcerf 不一致 | 上游仓库/源码包均叫 libcerf，C++ 库只是其中一个构建目标 | 配方复用 libcerf v3.3 源码包，仅开 CERF_CPP；PR 正文与 notes 如实说明拆包口径 (Alpine/Fedora/MSYS2 同例) |
| 2 | 上游默认同时构建 C 库/CLI/man | 默认 CERF_C/LIB_RUN/LIB_MAN 全开会产出多余产物 | 显式关闭 CERF_C/LIB_RUN/LIB_MAN，保持纯库包，无需 commands.json |
| 3 | Windows 检出工作树恒显示 libXext 脏 | 上游同时存在 archives/l/libXext 与 archives/l/libxext，Windows 大小写不敏感文件系统无法共存 | 与本包无关；本 PR 仅含 archives/l/libcerfcpp，HMBS 后端在大小写敏感环境提交时不受影响 |

## 源码修改

无补丁 (patches_applied 为空)。POSIX 兼容，无需平台宏。

## 依赖版本

无外部依赖 (dependencies 为空)。系统库仅链接 `m` (Linux/OHOS)。

## 验证结果

待 HMBS 真机预检 (conan create) 返回后回填:
- 上游 ctest 执行数/通过数 (预期 9/9，以实测为准)
- test_package 6/6 CHECK-OK

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libcerfcpp/3.3/conanfile.py | 主配方 (CMake) |
| archives/l/libcerfcpp/3.3/conandata.yml | 源码 URL + sha256 |
| archives/l/libcerfcpp/3.3/manifest.yaml | 版本级 manifest |
| archives/l/libcerfcpp/3.3/test_package/ | 消费者测试 (真实 API 调用) |
| archives/l/libcerfcpp/3.3/notes.md | 本文件 |
| archives/l/libcerfcpp/manifest.yaml | 软件级 manifest |
| archives/l/libcerfcpp/README.md | 软件说明 |

## 注意事项

- 本机为 Windows，不运行 conan；一切编译与测试结论以真机预检日志为准
- 真机与命令细节属于内部基建，不写入 PR 正文；正文统一写「在 HarmonyOS aarch64 环境实测」
- 消费者测试故意使用宽松容差 (1e-9~1e-12)，避免 last-bit 差异导致误报；
  上游官方回归测试仍在 build() 全量执行，不用消费者测试替代
