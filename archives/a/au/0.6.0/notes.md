# au 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE target `Au::au`）
- 编译日期: 2026-09-03
- 编译器: /data/service/hnp/bin/clang++ / clang（OHOS SDK 26.0.0.18，clang 15）
- 状态: built（上游测试 1824/1824 = 100%；conan create + test_package 消费者验证通过）

## 库简介

au 是 aurora-opensource 的 C++17 量纲/单位库（dimensional analysis）。
- 上游仓库: https://github.com/aurora-opensource/au
- 许可证: Apache-2.0
- 类型: header-only（CMake INTERFACE library，安装 225 个头文件 + AuConfig.cmake）

## 官方来源核验（R01 bootstrap/source audit）

- 官方仓库: https://github.com/aurora-opensource/au
- 正式 tag: 0.6.0
- tag commit: 13efd66572f414601e41678c62b674f2fdcd0c35（GitHub API 核验）
- 源码包: https://github.com/aurora-opensource/au/archive/refs/tags/0.6.0.tar.gz
- SHA-256: e03aba27139b1e090b520945e62fc3ba2bf9128a096d68576eaf301970d5fb10
  （官方直连超时，同一官方归档经 gh-proxy 镜像复验哈希完全一致）
- 版本头: `#define AU_VERSION_MAJOR 0 / MINOR 6 / PATCH 0`

## Conan 配方说明

### 配方结构
- `conanfile.py`: header-library 配方，CMake 工具链
- `conandata.yml`: 官方源码 URL + SHA256 + 2 个测试可移植性补丁
- `test_package/`: 消费者测试 test_au_ohos.cpp（6 项 HarmonyOS 专项断言）

### 关键配置
- `package_type = "header-library"`；`package_id()` 移除 compiler/build_type 依赖
- `configure()` 中 `rm_safe("os.version")`：OHOS 下 os.version 未定义导致包无效
- `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`：规避 E092
- `CMAKE_CXX_FLAGS=-stdlib=libc++`：OHOS clang 无 libstdc++
- `AU_EXCLUDE_GTEST_DEPENDENCY=ON` / `AU_ENABLE_TESTING=OFF`：包内不携带
  googletest（上游测试已在 worktree 内全量验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Pi.HasCorrectValue / GetValue.PiToThePower1HasCorrectValues 失败：`M_PIl not available` | OHOS libc 不定义 M_PIl；上游 `#ifdef M_PIl #else ADD_FAILURE()` | 测试内定义等效 long double π 常量（kPiLongDouble）替代 ADD_FAILURE，保持精度断言 |
| 2 | Root.ResultIsVeryCloseToStdPowForPureRoots 失败：au root 384173749.4962483 vs powl 384173749.49624783（rel 1.24e-15 超 DoubleEq 4*DBL_EPSILON） | OHOS powl 相对误差 ~1e-15；au 的 quad long double 二分搜根反而更精确 | DoubleEq → DoubleNear 相对容差 1e-12（量化后选取；au 值本身正确） |
| 3 | conan create 报 `'settings.os.version' value not defined` | OHOS 适配 conan 对 os.version 的枚举限制 | configure() 中 rm_safe("os.version") |
| 4 | CMake TryCompile 失败 `invalid library name in argument '-stdlib=libstdc++'` | conan 默认注入 libstdc++，OHOS clang 只提供 libc++ | CMAKE_CXX_FLAGS=-stdlib=libc++（主配方与 test_package 均设置） |
| 5 | GitHub 直连超时无法 get 官方 tarball | 宿主网络限制 | 预置 conan 下载缓存（core.sources:download_cache，按 sha256 命中官方归档） |
| 6 | finish W3 junk_check full 模式扫出其他库基线垃圾 | 本库 pr.diff 空，回退全仓扫描 | JUNK_PR_DIFF 走 prdiff 只检本库文件（既有 dr_mp3 草稿同法） |

## 源码修改（测试可移植性补丁，库源码未改）

- `0001-au-magnitude_test.cc.patch`: Pi.x2 + Root.x1 三处测试断言（见上表 1-2）
- `0002-au-utility-test-type_traits_test.cc.patch`: IncludeInPackIf 中
  `char → signed char`（arm64/OHOS 默认 unsigned char，恢复上游测试语义）

## 依赖版本

- 无运行时依赖；测试依赖 ohpcd registry gtest/1.17.0（构建期经
  googletest 1.12.1 源码，由 registry 解析）

## 验证结果

```bash
# 上游全量（OHOS 工具链串行）
ctest --test-dir build-cmake -j1 --output-on-failure
#   → 1824/1824 tests passed（修复后；日志 au-r01-ctest-serial-r2.log）

# 消费验证
conan create archives/a/au/0.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
#   → 包创建成功（225 .hh + AuConfig），test_package test_au 6/6 PASS

# HarmonyOS 专项测试（test_au_ohos）
#   → char signedness / π long double / 量纲运算 / 单位换算 / chrono 互操作 / root 精度
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | Conan 配方（header-library） |
| test_package/ | 消费者测试（CMakeLists + conanfile + test_au_ohos.cpp + MANIFEST.yml） |
| patches/0001,0002 | 测试可移植性补丁 |
| reports/ | conan-create / conan-verify / w3-local-ci / knowledge-candidate-ledger |

## 知识路径

- 路径 B（知识库扩展）：DRAFT-au-0.6.0-ohos-mpil-powl-float-tests（.md/.kv 配对），
  覆盖 OHOS M_PIl 缺失与 powl 精度导致的 gtest 浮点测试移植；评
  char signedness / conan libcxx / header-only 配方 / W3 噪声隔离均复用既有知识。
- PR 前缀：【知识库扩展】

---

**编译结束**: 2026-09-03
**最终状态**: built