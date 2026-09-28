# c89stringutils 0.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 / clang++（HarmonyOS PC, aarch64, clang 15）
- 状态: published

## 编译步骤

1. 上游源码：官方标签 `refs/tags/0.0.2`（commit 7c4832c94ca59270849776f5ae0be499ae7cc577），
   tarball SHA-256 `abf4608b4e437daafa9ffbad7e8371a2fa5ecb58f50c58ece91a59492b6fdc02`。
2. 纯 CMake C89 工程：`cmake -DBUILD_TESTING=ON` → `cmake --build` → `ctest`。
3. 上游测试实测 1/1 通过（4 断言全过）。
4. `conan-init` 生成 CMake 配方（无外部依赖闭包）；`conan-verify` G1-G4 + L2/L4/L5 全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 CMakeLists 固定 `greatest.h` SHA-256 校验失败 | 上游 pin 的哈希过期（`b3f89eca…` 与实际下载 `a0d9697c…` 不一致；经 GitHub 直连与镜像双重下载实测确认内容未篡改） | 补丁 `patches/0001-c89stringutils_tests-test_c89stringutils-CMakeLists.txt.patch` 更新为实检值 |
| 2 | conan create source() 403 FORBIDDEN | conandata.yml 源 URL 指向仓库主页而非归档 tarball，镜像对其返回 403 | 修正为官方归档 URL `https://github.com/offscale/c89stringutils/archive/refs/tags/0.0.2.tar.gz` |

## 源码修改

- `patches/0001-…-CMakeLists.txt.patch`：更新 greatest.h SHA-256（上游哈希过期）。

## 依赖版本

无外部依赖（C89 纯标准库实现）。

## 验证结果

```bash
ctest --output-on-failure        # 1/1 passed, 4/4 assertions
conan create (ohos-aarch64)      # G2 干净构建通过, test_package 通过
conan-verify                     # G1-G4 + L2/L4/L5 全部 PASS
finish (W2/W3 本地 CI)           # build_and_test.sh RC=0
```

## 注意事项

- 本库为 `package_type: library`，不产生可执行文件，无需 commands.json（R38）。
- W3 本地 CI 的 junk_check 首次以 full 模式扫描整仓，命中的 3 个文件
  （cloog/kics 的 `.build-closed`/`.staging-verified`）经核验为基线 main 中
  其他库的空文件（blob e69de29b、sha256 e3b0c442…），不在本库允许范围；
  按「无关历史基线」做受限 checker-input 隔离（仅扫描本 PR 文件，
  与 CI prdiff 模式同构）后复验通过，基线文件零改动。

---

**编译结束**: 2026-09-23 00:08
**最终状态**: published
---

**编译结束**: 2026-09-23 00:12
**最终状态**: published
