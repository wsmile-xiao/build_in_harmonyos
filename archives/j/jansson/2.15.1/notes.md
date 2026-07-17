# jansson 2.15.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/akheron/jansson/archive/refs/tags/v2.15.1.tar.gz
2. 因缺少 automake 无法使用 autotools，使用 CMake 构建
3. CMake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DJANSSON_BUILD_SHARED_LIBS=ON`
4. 编译: `make -j2`
5. 测试: `ctest --output-on-failure` — 全部 215 个测试通过 (100%)
6. 安装: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法生成 configure 脚本 | 缺少 automake | 使用 CMake 构建系统 |

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- 无外部运行时依赖（仅需 libc）

## 验证结果

```bash
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 215
Total Test time (real) = 4.71 sec
```

## 注意事项

- jansson 同时支持 autotools 和 CMake，在缺少 automake 时可使用 CMake 构建
- 所有 215 个测试通过，无平台兼容性问题
- 无需任何补丁

---

**编译结束**: 2026-07-15 14:30
**最终状态**: built

## 二次校准 (2026-07-17)

- Rebased on latest main
- 验证所有检视意见已修复 (R39 mirror URLs, test.c NULL check, shared option mapping)
- conan create 本地验证通过: 215/215 tests + test_package 通过
- 所有检视意见已在 PR 中标记为已解决
