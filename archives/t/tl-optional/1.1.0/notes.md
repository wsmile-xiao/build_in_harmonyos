# tl-optional 1.1.0 适配笔记

## 基本信息
- **上游**: https://github.com/TartanLlama/optional
- **版本**: 1.1.0（标签 v1.1.0，commit 3a1209de8370bf5fe16362934956144b49591565）
- **许可证**: CC0-1.0
- **类型**: header-only C++11/14/17 库（单个 `include/tl/optional.hpp`，约 35KB）
- **官方归档**: https://github.com/TartanLlama/optional/archive/refs/tags/v1.1.0.tar.gz
- **SHA-256**: 88ece79f3de5ccaec4191951a222f95cc80c4381dafd3163bdb1ff87cedf3118
- **交叉核验**: 标签 commit 3a1209de 的原始 `include/tl/optional.hpp` SHA-256 与归档内文件完全一致（cd4f4703554a12c9aed7c2844e41b380fbc10a42dd2b783265d998ec8a0d31d6）

## 构建系统
- CMake，header-only INTERFACE library（`add_library(optional INTERFACE)` + alias `tl::optional`）
- `OPTIONAL_BUILD_TESTS=ON` 启用上游测试（Catch2 via FetchContent）
- `OPTIONAL_BUILD_PACKAGE=OFF` 关闭打包（Deb/RPM/MSI 无平台支持）
- CMake 配置安装: `lib/cmake/tl-optional/` + config/version 文件

## 编译环境
- 编译器: clang 15.0.4（OHOS 交叉工具链 `/data/service/hnp/bin/clang++`，target aarch64-unknown-linux-ohos）
- Conan 2.29.1，profile `ohos-aarch64`（os=OHOS, arch=armv8, cppstd=17, libc++）
- 执行端网络到上游 GitHub 曾不可达，经组织批准的 gh-proxy.com 镜像下载归档，并以官方标签 commit + SHA-256 交叉核验一致（conandata.yml 保持官方 URL）

## 编译步骤
1. `cmake -B build -DCMAKE_INSTALL_PREFIX=... -DOPTIONAL_BUILD_TESTS=ON -DOPTIONAL_BUILD_PACKAGE=OFF` — 配置通过
2. `cmake --build build -j4` — 全部 15 个测试可执行编译成功，exit 0
3. `ctest --test-dir build --output-on-failure` — 15/15 全部通过（0 失败），exit 0
4. `conan create archives/t/tl-optional/1.1.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` — 通过：
   - test_package 消费者测试 `test_optional.cpp` 真实编译运行：18 checks OK
   - HarmonyOS 专项测试 `harmonyos_specific_test.cpp` 真实编译运行：5 checks OK（platform=OHOS）
5. `conan-verify tl-optional 1.1.0` — G1（配方完整性）G2（conan create）G3（系统同名库隔离）G4（产物完整性）全部 PASS，报告可标 published

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 GitHub 直连不可达（git ls-remote exit 124 / curl exit 28） | 执行端网络到 github.com 的连接被阻断 | 经组织批准的 gh-proxy.com 镜像下载归档；保持 conandata.yml 官方 URL，以官方 tag commit + SHA-256 交叉核验一致；网络恢复后 conan create 直连官方 URL 成功 |
| 2 | conan-init 生成的 Autotools 模板与 CMake header-only 库不匹配 | 模板按构建系统猜测（autotools） | 重写 conanfile.py 为 CMakeToolchain header-library 模式（参照 sibling optional-lite 先例） |
| 3 | conan-verify G1 报缺 export_sources()/apply_conandata_patches | G1 硬校验要求这两个方法存在 | 无补丁包按标准 no-op 形态补上（export_conandata_patches + apply_conandata_patches），G1 通过 |
| 4 | 本地 W3（finish step5）整仓 junk check 误报失败 | full 模式扫描整仓 git ls-files，命中其他库已提交基线文件（goaccess tarball、scudo-malloc 标记文件），非 tl-optional 引入（本分支对这些路径 diff=0） | 按 SKILL 精确隔离/哈希记录基线噪声（见 .atomcode-oh/logs/w3_baseline_noise_tl-optional.log）；真实 CI 用 prdiff/incremental 模式只查 PR 改动文件，本库改动无 junk，不受影响 |

## 源码修改
- `include/tl/optional.hpp`: 无修改（零补丁、零源码改动）
- patches/: 0 个

## OHOS 适配
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（CMake 不识别 OHOS，E092 规避，同 optional-lite 先例）
- 无平台特定代码修改；C++17 + libc++ 下全部 API 正常

## 知识路径判断
- `path_a_no_knowledge`: 本适配为常规 header-only 基础适配，官方源+标签+SHA-256 可核验、零补丁零依赖、conan-verify 与上游测试全通过；无通用可复用新问题，无知识库扩展需求。知识图谱查重无命中（无 optional/TartanLlama 相关条目）。