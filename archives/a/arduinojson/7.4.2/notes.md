# arduinojson 7.4.2 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4（libc++-ohos）
- 状态: built

## 编译步骤

```bash
# 官方 tag 源码（GitHub API 核验 v7.4.2，commit ed69feadb95182dc53ac978975d310122060a767）
python3 scripts/ohc-run.py init-build arduinojson 7.4.2 --url=https://github.com/bblanchon/ArduinoJson/archive/refs/tags/v7.4.2.tar.gz
# 语言预检
python3 scripts/ohc-run.py lang-preflight arduinojson 7.4.2 --src $BUILD_SRC_DIR
# 上游测试（Catch 框架，extras/tests）
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build --target <20 个 Tests 目标> -j4
ctest --output-on-failure -E fuzzer   # 27/27 通过
# Conan 配方生成与验证
python3 scripts/ohc-run.py conan-init arduinojson 7.4.2
python3 scripts/ohc-run.py conan-verify arduinojson 7.4.2   # G0-G4+L2/L4/L5 全 PASS
# 收尾（W3 阻塞门禁通过）
python3 scripts/ohc-run.py finish arduinojson 7.4.2 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create G2 失败：`undefined symbol: std::__h::ios_base::init(void*)` 等 | CMake `BUILD_TESTING` 默认 ON，触发 extras/fuzzing 链接 `libclang_rt.fuzzer.a`，该库按系统 libc++ 编译而 OHOS 用 `std::__h` 命名空间 ABI，符号不匹配 | conanfile.py 的 `build()` 中 `cmake.configure(variables={"BUILD_TESTING": "OFF"})`；上游测试独立验证并记录于 MANIFEST.yml |
| 2 | test_package 构建失败：`Cannot determine link language for target "test_arduinojson"` | 测试源文件名为 test.c，CMake 无法判定 C++ 链接语言 | 改名为 test.cpp 并同步 CMakeLists.txt / MANIFEST.yml |
| 3 | W3 junk_check 全仓扫描命中 9 个文件 | 均为 main 分支其他库目录 TRACKED-in-main 的历史基线垃圾（embree/flatcv/libmorton/goaccess/captagent/lsof/scudo-malloc/stb_image），不在当前库 delivery_allowed_paths | 按 oh-executor 基线隔离：生成仅含当前库 8 个 PR 文件的 pr.diff（sha256=e741cb...），junk_check 以 CI 同口径 prdiff 模式复验通过后删除，见工作区审计记录 |
| 4 | G0 clean-verify configure exit 127 | manifest build_system 是模板占位符 `{BUILD_SYSTEM}`，G0 误跑 ./configure；ArduinoJson 是 CMake 工程无 configure 脚本 | manifest.yaml 填 `build_system: cmake`、`build.system: cmake`、补 sha256 |

## 源码修改

无（纯 header-only 适配，无补丁）。

## 依赖版本

无第三方依赖（header-only 标准库实现）。

## 验证结果

```bash
# 上游测试：27/27 通过（ctest -E fuzzer，Catch 框架）
# 本机手工构建（非 conan 路径）：20 个 Tests 目标全部构建成功，27/27 通过
# conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
# test_package（ohos-aarch64 profile）：100% tests passed (1/1)
# W3 本地 CI 模拟：通过
```

## 交付物

header-only 库，无二进制打包产物；conan 包仅含 include/ 头文件。

## 注意事项

- fuzzing 目标在 OHOS 上不可链接（libclang_rt.fuzzer.a ABI 不匹配），属工具链限制，非上游缺陷；已通过 BUILD_TESTING=OFF 在 conan 构建中排除，上游测试不受影响。
- test_package 必须使用 .cpp 扩展名（R34 真实调用 API）。
---

**编译结束**: 2026-09-03 06:45
**最终状态**: published
