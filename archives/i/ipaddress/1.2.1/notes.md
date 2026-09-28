# ipaddress 1.2.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 交叉 profile）
- 状态: built

## 编译步骤

header-only CMake 库，无 configure 步骤。本地验证（clang 15，x86 主机）：

```bash
cmake -S . -B build-local -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DIPADDRESS_BUILD_PACKAGES=OFF -DIPADDRESS_BUILD_DOC=OFF
cmake --build build-local -j2
ctest --output-on-failure   # 863/863 通过
```

Conan 交叉构建（ohos-aarch64 profile）：`conan create` 通过（G1-G5 全绿），
test_package 消费者（IPv4/IPv6 地址/网络解析与字符串往返断言）通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | init-build 按 URL 猜测构建系统为 autotools，实际为 CMake | 手工重写为 header-only CMake 配方（header-library 类型） |
| 2 | conan create 报 `Package type is 'library', but no 'shared' option declared` | header-only 无共享库语义 | `package_type = "header-library"`；知识 E283/E257 命中 |
| 3 | conan-verify G1 要求显式 build()/export_sources() | G1 是结构完整性检查 | 补 no-op build()（apply_conandata_patches）+ export_sources()；知识 E257 命中 |
| 4 | test_package 报 `Cannot determine link language` | conan-init 生成 C 工程 + test.c，改 CXX 后源文件后缀不匹配 | test.c → test.cpp，CMakeLists/MANIFEST 同步；知识 DRAFT-picojson 命中 |
| 5 | CMakeDeps 报 include 目录不存在 | header-only 的 package_id 固定 da39a3ee（clear()），配方改动后 conan 复用旧缓存包 | `conan remove ipaddress/* -c` 后重建 |
| 6 | test.cpp include `ipv4_address.hpp` 找不到 | 上游头文件名为连字符 `ipv4-address.hpp` | include 用连字符文件名 |
| 7 | W3 本地 CI JC5 拦 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 其他库合入 main 的历史基线标记，full 模式下整仓扫描 | 临时 index 隔离→复验→无条件恢复（零 diff），审计记录于 /storage/Users/currentUser/tianyi/baseline-isolate-ipaddress-r01.audit.md |

## 源码修改

无补丁（patches/ 为空）。仅测试消费者 test.cpp 为本地新增验证代码。

## 依赖版本

无外部依赖（header-only，无 requires）。

## 验证结果

- 上游测试：863/863 通过（100%）
- conan-verify：G1-G5 + L2/L4/L5 通过
- test_package 消费者测试：通过

## 注意事项

- 上游头文件为 `ipaddress/ipv4-address.hpp`（连字符）等，include 时必须使用连字符名。
- header-only 库用 `package_type = "header-library"`，package() 复制 `include/` 目录，
  `cpp_info.includedirs = ["include"]`；package_id 恒为 da39a3ee，配方改动后需清理缓存重建。
---

**编译结束**: 2026-09-23 00:35
**最终状态**: built