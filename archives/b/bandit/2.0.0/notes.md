# bandit 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (ohos-sdk 26.0.0.18 / libcxx-ohos) / aarch64
- 状态: built

## 编译步骤

```bash
# 1. 源码获取（官方 GitHub 归档 + submodule 按锁定 commit 补齐）
cd ~/tmp/builds/bandit-2.0.0.work
# bandit v2.0.0 tarball: https://github.com/banditcpp/bandit/archive/v2.0.0.tar.gz
#   sha256 e86b7c60753d828149a42298152f807c8020f9905f410acb9e45d87f4ea22a5e
# snowhouse @34d4b6df: https://codeload.github.com/joakimkarlsson/snowhouse/tar.gz/34d4b6df949356bcc0814f976f015ebee6ced9b3
#   sha256 71e4afddd2bf66fa14e96e3fb3e66edc1f9a233d56dab60482ca5b393a865a72
# cotire @d0eadcd2: https://codeload.github.com/sakra/cotire/tar.gz/d0eadcd2a230a8701d5310e34cc45ea9d6649df2
#   sha256 3fdb11de76f465dfa228c846e72f48fbe8d1bca119891076187d3b7ae6e67c89

# 2. 配置（CMake 4.x 已移除 <3.5 兼容，需策略参数）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# 3. 编译（仅 bandit-specs；snowhouse 样例文件为 Latin-1 编码，
#    不参与产品构建，--Wno-invalid-utf8 或跳过 snowhouse-tests 目标）
CMAKE_POLICY_VERSION_MINIMUM=3.5 make -C build bandit-specs

# 4. 运行上游自测套件
./build/bin/bandit-specs --no-color --reporter=dots
./build/bin/bandit-specs --no-color --reporter=xunit
# 结果: 310 通过 / 4 跳过 / 0 失败（注册 314）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 官方 tarball 不含 git submodule（snowhouse/cotire 目录为空），bandit.h 强依赖 `bandit/assertion_frameworks/snowhouse/snowhouse/snowhouse.h` | GitHub archive 不含 submodule | 用 GitHub API 解析 v2.0.0 的 locked commit（snowhouse 34d4b6d、cotire d0eadcd），从官方源下载补齐，并在报告/conandata 记录 SHA-256 |
| 2 | CMake configure 报 `Compatibility with CMake < 3.5 has been removed` | bandit(2.8)/cotire 的 cmake_minimum_required 过旧，CMake 4.x 移除兼容 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（cotire 构建期需 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 环境变量） |
| 3 | snowhouse 样例（框架自带 example，非产品）以 Latin-1 编码含非法 UTF-8 注释，clang 报 `invalid UTF-8 in comment` 致命错误 | 2009-2012 年代源码编码问题 | 仅构建 bandit-specs 目标；样例不计入上游测试统计 |
| 4 | `-Werror,-Wdelete-abstract-non-virtual-dtor`：`bandit::detail::failure_formatter` 抽象基类无虚析构，被 libc++-ohos delete | bandit 2.0.0 真实源码缺陷（2015 年代代码） | 补丁 `0001-failure-formatter-virtual-dtor.patch`：为 failure_formatter 增加 `virtual ~failure_formatter() {}` |

## 源码修改

- `patches/0001-failure-formatter-virtual-dtor.patch`：`bandit/failure_formatters/failure_formatter.h` 增加虚析构（由 finish refresh-patch 生成）

## 依赖版本

- 无外部 Conan 依赖（纯头文件 C++11 库）; 构建期 submodule: snowhouse@34d4b6d, cotire@d0eadcd2

## 验证结果

```bash
# 上游自测（bandit-specs，注册 314 项 / 通过 310 / 跳过 4 / 失败 0）
# 全量通过率: 310/370 源码声明 = 83.8% 口径说明见 reports/test-ledger.md
# 鸿蒙专项测试: tests/ohos_spec.cpp 编译运行通过
# 消费者用例: 通过已发布公开头文件编译链接运行通过（见 reports/consumer-verification.md）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan2 配方（纯头文件打包 bandit + snowhouse 头树） |
| conandata.yml | 官方多源声明（bandit + snowhouse + cotire + sha256） |
| test_package/ | 消费者用例（编译链接运行 bandit 公开 API） |
| patches/0001-*.patch | failure_formatter 虚析构适配补丁 |
| tests/ohos_spec.cpp | 鸿蒙专项测试（aarch64-ohos clang 实际编译运行） |

## 注意事项

- bandit 是 C++11 BDD 测试框架（header-only），产品交付物为头文件，无 bin/lib 产物，属库类型：不需要 commands.json（R38）
- conandata 必须多源：仅 bandit tarball 无法编译（submodule 缺失）
- `it(` 计数含 it.spec.cpp 中对 it() API 的显式重载/mock 调用，需按台账口径区分（370 声明 vs 314 注册 vs 310 通过）
---

**编译结束**: 2026-09-19 04:13
**最终状态**: built
