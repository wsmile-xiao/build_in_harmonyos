# picosha2 1.0.1 适配笔记

## 编译环境
- 构建系统: headeronly（header-only C++ 库，CMake INTERFACE 工程，SKILL §12 无构建族 A）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (aarch64)
- 状态: published

## 编译步骤

1. `ohc-run.py init-build picosha2 1.0.1 --auto --url=https://github.com/okdshin/PicoSHA2/archive/refs/tags/v1.0.1.tar.gz`（源码下载+解压+基线指纹）
2. `ohc-run.py lang-preflight picosha2 1.0.1 --src $BUILD_SRC_DIR` — task=cpp, detected=cpp (cmake), 通过
3. 上游测试：构建 `test/` 的 CTest 单测（test.cpp 实际调用 picosha2 接口并断言已知哈希）
4. `ohc-run.py conan-init picosha2 1.0.1` → 生成 conanfile.py（headeronly 模板）+ conandata.yml + test_package/
5. `ohc-run.py conan-verify picosha2 1.0.1` → G0-G4 + L2/L4/L5 八道门禁
6. `ohc-run.py finish picosha2 1.0.1 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ohc-run.py build` 在 [5/14] make install 报"安装无产物" | picosha2 为 header-only INTERFACE 库，上游 CMakeLists.txt 无 install 规则、无 bin/lib 产物；driver Step5 只统计 bin/ 与 lib/ 产物 | 按 SKILL §12 无构建族判定为 headeronly，不走 make install 产物门禁；以 conan-verify G2（conan create 从干净源码构建）为真实构建门禁 |

## 源码修改

无（header-only 库，无需源码补丁；随包仅含 picosha2.h 单一头文件）

## 依赖版本

无外部编译依赖（header-only，无 requires）

## 验证结果

```bash
# 上游测试（test/CTest：unittest 断言 RFC 测试向量）
ctest --test-dir build --output-on-failure   # 通过
# Conan 配方自包含构建验证（G2）
conan create ... picosha2/1.0.1@   # 通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | - | headeronly 配方，package() 安装 picosha2.h 至 include/ |
| conandata.yml | - | 官方 v1.0.1 标签 tarball + sha256 |
| test_package/ | - | 消费者测试：实际 include picosha2.h 并计算已知哈希（R34） |

## 注意事项

- 上游版本标识核验：GitHub 官方标签 v1.0.1（release commit 161cb3f），sha256=9983136544234e573fe07cc1a22fdf978ad7979043e7be2e9082f6d4991ff8a8，与官方标签 tarball 一致。
- R26 系统同名库隔离：无 .so 产物，不适用。
- commands.json：无可执行产物，不需要。
---

**编译结束**: 2026-09-05 22:29
**最终状态**: built
