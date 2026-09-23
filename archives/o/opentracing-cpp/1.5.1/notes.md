# opentracing-cpp 1.5.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

```bash
# 源码获取（GitHub 直连超时，init-build 下载阶段经 gh-proxy.com 镜像获取官方 v1.5.1 tag tarball，sha256 已核验）
mkdir -p ~/tmp/builds && cd ~/tmp/builds
curl -fsSL -o opentracing-cpp-1.5.1.tar.gz 'https://gh-proxy.com/https://github.com/opentracing/opentracing-cpp/archive/refs/tags/v1.5.1.tar.gz'
sha256sum opentracing-cpp-1.5.1.tar.gz   # 015c4187f7a6426a2b5196f0ccd982aa87f010cf61f507ae3ce5c90523f92301

# init-build（tarball 就绪后跳过下载）
cd build_in_harmonyos && python3 scripts/ohc-run.py init-build opentracing-cpp 1.5.1 --url=https://github.com/opentracing/opentracing-cpp

# lang-preflight 语言预检（R47）→ 通过

# CMake 配置 + 编译（手工探索期，含测试）
cd $BUILD_SRC_DIR && mkdir -p .build && cd .build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_TESTING=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_DYNAMIC_LOADING=ON -DUNIX=ON
make -j2
make install DESTDIR=$TEST_PREFIX
ctest  # 11/11 通过（需 LD_LIBRARY_PATH + mocktracer/example output 链接，见下）

# Conan 配方验证（生产路径）
python3 scripts/ohc-run.py conan-verify opentracing-cpp 1.5.1   # G0-G4/L2/L4/L5 全 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 超时 | 本机到 github.com 直连端口 443 连接超时（镜像可达） | 用 gh-proxy.com 镜像预下载官方 tarball 到 `~/tmp/builds/`，init-build 复用；conandata.yml 保持官方 URL（R39），CI mirror fallback 机制同源 |
| 2 | CMake 4.1.2 报 "Compatibility with CMake < 3.5 has been removed" | 上游 `cmake_minimum_required(VERSION 3.1)`；CMake ≥4.x 移除了 <3.5 策略支持 | 补丁 `0001-CMakeLists.txt.patch`：3.1→3.5（参考 abpoa 1.5.6 同款处理）；生成方式必须用 `refresh-patch --auto`（手写 patch 会被 conan patch 解析器判 stream incomplete） |
| 3 | 手工 ctest 5/9 失败 "Error loading shared library ../output/libopentracing.so" | 上游 CMake 把产物集中到 `output/`，DT_NEEDED 使用相对路径（`../output/...`），OHOS musl 加载器按 cwd 解析；mocktracer/example 测试从子构建目录运行 | 运行时恢复：`.build/mocktracer/output` 与 `.build/example/output` 建 libopentracing.so 符号链接 + `LD_LIBRARY_PATH=$PWD/output` 后 ctest 11/11 通过（未修改上游源码） |
| 4 | dynamic_load_test / multiple_tracer_link_test 未实例化 | 上游 `if (NOT SUPPORTS_WEAK_SYMBOLS OR NOT UNIX)` 在 OHOS（CMake 不识别为 UNIX）强制关闭 BUILD_DYNAMIC_LOADING | 探索期 `-DUNIX=ON -DBUILD_DYNAMIC_LOADING=ON` 后注册并 11/11 通过；配方内不开启（动态加载为可选特性，核心 API 不受影响） |
| 5 | conan verify G2 首次失败 | conandata.yml 中 conan-init 生成时自动注入的 `CMAKE_POLICY_VERSION_MINIMUM` toolchain 变量不生效（toolchain 在 cmake_minimum_required 后加载） | 改为源码补丁提升最低 CMake 版本（见 #2），从根上解决 |
| 6 | test_package 消费者编译失败 "no member named MakeNoopTracer" | consumer 测试漏 include 声明 MakeNoopTracer 的 `<opentracing/noop.h>` | test.cpp 补 `#include <opentracing/noop.h>` |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：`cmake_minimum_required(VERSION 3.1)` → `3.5`（CMake ≥4 兼容）

## 依赖版本

- 无外部 Conan 依赖（Catch2/mpark-variant/TartanLlama-expected 头由上游 3rd_party/ 自带）

## 验证结果

```bash
# 上游测试 11/11（10 个独立 TEST_CASE + 1 个链接用例，含恢复实例化的 dynamic_load/multiple_tracer_link）
ctest --output-on-failure   # 100% tests passed, 0 failed out of 11

# 消费者用例（test_package，真实公开 API 调用）
# 1/1 Test: consumer_opentracing Passed; 输出: consumer_opentracing: OK (noop tracer, spans, tags, logs)

# conan-verify
# Verdict: PASS；G0/G1/G2/G3/G4/L2/L4/L5 全通过
```

## 知识候选

- 候选 1：上游 CMake 相对路径 DT_NEEDED（`../output/...`）在 OHOS musl 加载器按 cwd 解析导致跨目录测试运行失败 → 运行时建 symbol link + LD_LIBRARY_PATH 恢复。可跨库复用（任何上游把产物集中 output/ 且用相对 NEEDED 的 CMake 库）。
- 候选 2：CMake ≥4 移除 <3.5 策略 → 对 `cmake_minimum_required < 3.5` 的上游库统一 bump 到 3.5（abpoa 1.5.6 已有先例，可能 fully duplicate）。
- 候选 3：OHOS 未被 CMake 识别为 UNIX → 上游 `NOT UNIX` 条件分支自动关闭的平台特性（BUILD_DYNAMIC_LOADING）探索期可 `-DUNIX=ON` 强制开启实例化测试。
---

**编译结束**: 2026-09-16 10:31
**最终状态**: built
