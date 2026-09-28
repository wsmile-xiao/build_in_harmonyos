# lunarlog 1.29.2 适配笔记

## 编译环境
- 构建系统: cmake (header-only, INTERFACE target)
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (OHOS toolchain, aarch64)
- 状态: published

## 编译步骤

```bash
# init-build: 官方 codeload tag v1.29.2
python3 scripts/ohc-run.py init-build lunarlog 1.29.2 --url=https://codeload.github.com/LunarECL/LunarLog/tar.gz/refs/tags/v1.29.2
# 手工构建 + 上游测试 (build/ 目录)
cmake -DCMAKE_BUILD_TYPE=Release -DLUNARLOG_BUILD_TESTS=ON -DLUNARLOG_BUILD_EXAMPLES=ON .. && make -j2 && ctest
# 配方
python3 scripts/ohc-run.py conan-init lunarlog 1.29.2
python3 scripts/ohc-run.py conan-verify lunarlog 1.29.2   # G0-G4+L2/L4/L5 全过
python3 scripts/ohc-run.py finish lunarlog 1.29.2 published # W2/W3 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan get() BadZipFile | codeload tar.gz URL basename 无扩展名, 按 zip 解压 (E276) | conandata.yml sources 显式 filename: lunarlog-1.29.2.tar.gz |
| 2 | CMakeToolchain 双声明 ConanException | generators 属性与 generate() 重复实例化 (ctre/shine 草稿) | 移除 generators 属性, 仅 generate() 内单次实例化 |
| 3 | 上游 11 项 culture 测试失败 | OHOS 无 locale 数据, std::locale("en_US") 构造成功但 classic 行为 (E023) | 库优雅回退, 测试断言失败为平台限制, 台账如实记录 |
| 4 | 上游 4 项 Subprocess aborted | gtest CaptureStderr 硬编码 /tmp (erofs 只读), TMPDIR 无效 | 新草稿 DRAFT-lunarlog-1.29.2-gtest-capture-tmpdir-ineffective |
| 5 | ConfigWatcherFileUnreadable 失败 | HMDFS chmod 000 不生效 (E046) | 台账记录平台限制 |
| 6 | W3 junk check 失败 | 其他库 (cloog/kics) 既有基线状态文件被 full 模式扫描 | 基线隔离复验 (git rm --cached → 复跑 → 恢复, SHA-256 一致) + prdiff 模式复跑 W3 通过 |

## 源码修改

无（header-only 库, 无需补丁）。

## 依赖版本

- googletest v1.15.2 (FetchContent, 仅测试)
- pthread (系统库)

## 验证结果

```bash
# 上游测试: 1157 用例, 1141 通过, 16 失败, 5 跳过 (98.6%)
# 鸿蒙专项: ohos_specific_test PASS (公开 API + 4 线程并发 + culture 回退)
# 消费者: test_package test.cpp, conan create 内 ctest 1/1 Passed
# conan-verify: G0/G1/G2/G3/G4/L2/L4/L5 全过
# W3 本地 CI 模拟: prdiff 模式 100% (1/1)
```
