# libyaml 0.2.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-14
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

1. 下载源码: https://github.com/yaml/libyaml/archive/refs/tags/0.2.5.tar.gz
2. CMake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
3. 编译: `make -j2`
4. 安装: `make install DESTDIR=$TEST_PREFIX`
5. 测试: `./test-version` (输出 sizeof(token/event/parser))

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败 | cmake_minimum_required(VERSION 3.0) 与 CMake 4.x 不兼容 | 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | test_package 链接失败 | CMakeDeps 生成的 target 名为 yaml 而非 yaml::yaml | CMakeLists.txt 中使用 yaml 而非 yaml::yaml |

## 依赖版本

无外部依赖。

## 验证结果

```bash
# conan create 验证通过 (G2 PASS)
# 本地 CI 模拟通过 (W3 PASS: setup.sh + build_and_test.sh)
# test_package 测试通过: yaml_parser_initialize/scan/delete 生命周期验证
```

---

**编译结束**: 2026-07-14
**最终状态**: published
