# kangaru 4.3.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 / clang++ (OHOS toolchain, /data/service/hnp/bin)
- 状态: built

## 编译步骤

kangaru 为 header-only CMake 库（`add_library(kangaru INTERFACE)` + install include/kangaru），无 configure/make 产物：

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH=<kgr-deps> \
    -DKANGARU_TEST=ON -DKANGARU_TEST_CXX14=ON -DKANGARU_TEST_CXX17=ON \
    -DKANGARU_REVERSE_DESTRUCTION=ON -DCMAKE_INSTALL_PREFIX=<prefix>
cmake --build build -j4        # 21 个测试目标全部编译
cmake --install build          # 安装 46 个头文件 + CMake package config
ctest --output-on-failure      # 21/21 通过
```

Conan 配方构建（ohos-aarch64 profile, clang15 + libc++17）：
```bash
conan create archives/k/kangaru/4.3.2 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
# G0-G4 + L2/L4/L5 全门禁通过；test_package 4 项断言 + ohos_portability 6 项断言全过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 官方 URL 直接下载超时 | 网络到 github.com 不可达 | 通过 ghfast.top 镜像下载官方 tag tarball（sha256 与官方一致）；conandata.yml 仍保留官方 URL，CI 自动注入镜像 |
| 2 | conan-init 生成 autotools 配方 | init-build 从 URL 猜测构建系统为 autotools | 按 cmake header-only 重写 conanfile.py（CMakeToolchain + CMakeDeps + header-library） |
| 3 | G2 失败：`find_package(Catch2)` 回退空 submodule | 官方 tarball 不含 test/third_party/Catch2 submodule（空目录） | recipe 增加 test_requires(catch2/2.13.10-r0) + CMakeDeps 生成 Catch2Config |
| 4 | G2 失败：`self.tested` AttributeError | Conan 2 无 `tested` 属性 | 去掉门控，始终启用上游测试（header-only 测试仅数秒） |
| 5 | test_package 编译错误（多处） | kangaru API 语义：single_service 需默认构造、emplace 仅限 single、瞬态 service 按值返回、容器拷贝已删除 | 按上游 default_services.cpp 模式修正测试断言 |
| 6 | W3 JC 误报 main 基线垃圾 | 本地分支无 commit 时 JC 回退 full 全仓扫描，撞上 main 中其他库历史垃圾文件 | 本地 commit 本库改动后 JC 走 incremental 只扫本库 diff |

## 源码修改

无需补丁（纯 header-only，无平台差分）。patches/ 为空。

## 依赖版本

- 运行时：无第三方依赖（header-only，C++11 标准库即可）
- 测试框架：catch2/2.13.10-r0（conan recipe test_requires，替代缺失的 submodule）

## 验证结果

```bash
# 上游测试（本地 + conan create 内）
ctest --output-on-failure   # 21/21 passed（含 4 个 noexcept 变体 + 2 个编译期 error 目标 + C++14/17 变体）
# 上游 109 个 TEST_CASE（test/src/*.cpp 枚举）全量通过率 100%（109/109 对应目标全绿）
# OHOS 专项可移植性测试
./test_kangaru_ohos         # kangaru-ohos-portability: 6/6 checks passed on OHOS
# test_package 消费者测试
./test_kangaru              # 4 项真实 API 断言通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | cmake header-library 配方（含上游测试集成 + OHOS 专项测试） |
| conandata.yml | 官方 tag v4.3.2 tarball + SHA-256 ed2dec53… |
| test_package/ | test.cpp（4 断言）+ ohos_portability.cpp（6 断言）+ manifest |
| reports/ | source-audit.log / test-run-ledger.log / conan-verify-report.md |

## 注意事项

- 上游测试框架 Catch2 以 submodule 形式存在但官方 tarball 不含内容，须经 conan catch2 提供（同 abletonlink 的 asio 处理模式）
- 该库为 `【依赖项】` 身份：作为其他库的 DI 依赖，无独立运行时依赖链
---

**编译结束**: 2026-09-02 23:31
**最终状态**: published
