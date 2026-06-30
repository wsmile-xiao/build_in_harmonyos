# tinytoml 0.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-25
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: published

## 编译步骤

1. 从 GitHub 下载 tag 0.4 的 tarball（原 savannah.nongnu.org URL 404）
2. init-build 自动提取并检测嵌套源码（src/ 被提升到顶层）
3. 手动恢复 include/ 和 testcase/ 目录（提升时丢失）
4. 修改 CMakeLists.txt 路径：`../include` → `include`，`../testcase` → `testcase`
5. CMake 配置：`cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
6. 构建：`make -j2`（全部 8 个测试目标编译成功）
7. 测试：`make test`（8/8 通过）
8. Staging 安装：手动复制 `include/toml/toml.h` 到 `$TEST_PREFIX/$DEFAULT_PREFIX/include/toml/`
9. 打包：`ohc-run.py package` 生成 `tinytoml-0.4.0-ohos-aarch64.tar.gz`
10. 本地安装：复制到 `$DEFAULT_PREFIX/include/toml/toml.h`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL 404 | savannah.nongnu.org 上不存在 tinytoml-0.4.0.tar.gz | 改用 GitHub tag 0.4: https://github.com/mayah/tinytoml/archive/refs/tags/0.4.tar.gz |
| 2 | SSL 证书验证失败 | 鸿蒙平台缺少 CA 证书 | init-build 自动安装 CA 证书（121 个根证书） |
| 3 | include/ 目录丢失 | _promote_nested_source 提升 src/ 到顶层时删除了 include/ | 手动从 tarball 恢复 include/ 和 testcase/ 目录 |
| 4 | CMakeLists.txt 路径错误 | 提升后 ../include 和 ../testcase 路径失效 | 修改为 include 和 testcase（track-edit 追踪） |
| 5 | CMake 4.x 不兼容 | cmake_minimum_required(VERSION 2.8) 在 CMake 4.1.2 中报错 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 6 | manifest 缺少 build_system 字段 | G4 门禁检查 build_system 字段 | 在 manifest.yaml 中添加 build_system: cmake |
| 7 | 构建系统类型错误 | init-build 从 URL 猜测为 autotools | 修正为 cmake |

## 源码修改

- CMakeLists.txt: 修正 include 和 testcase 路径（从 `../include` → `include`，`../testcase` → `testcase`），因嵌套源码提升后路径变化

## 依赖版本

- CMake 4.1.2
- Clang 15.0.4
- GNU Make 4.4.1
- 无外部库依赖（header-only 库，gtest 1.7.0 随源码捆绑）

## 验证结果

### 编译时单元测试
```
make test 输出:
  8/8 tests passed, 0 tests failed
  Total Test time = 0.22s
```

### 鸿蒙平台功能测试（76 项全部通过）

| 测试套件 | 用例数 | 通过 | 失败 | 通过率 |
|----------|--------|------|------|--------|
| CMake 单元测试 (make test) | 8 | 8 | 0 | 100% |
| 官方 Testcase 验证 (success + fail) | 40 | 40 | 0 | 100% |
| 鸿蒙平台功能测试 (自编) | 28 | 28 | 0 | 100% |
| **合计** | **76** | **76** | **0** | **100%** |

功能测试覆盖：
- 数据类型: 字符串/整数/浮点/布尔/数组/表/内联表/数组表/日期时间/多行字符串/字面量字符串/转义字符
- 核心 API: parse/parseFile/find(路径导航)/get<T>/is<T>/as<T>/has()/setChild()/write()/operator<</find(index)
- I/O: 文件解析/流解析/空输入
- 错误处理: 无效整数/未闭合字符串/无效数组
- 高级: int64大整数/深层嵌套表/Writer往返序列化

命令行工具验证:
- parse_stdin: 正确从 stdin 解析 TOML 并格式化输出
- parse_file: 正确解析 TOML 文件并输出结果

详细报告见 reports/test-report.md

### 结论
tinytoml v0.4.0 在 OpenHarmony (aarch64) 平台上功能完全正常，无平台兼容性问题。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tinytoml-0.4.0-ohos-aarch64.tar.gz | 64KB | 预编译包（header-only，包含 toml.h + LICENSE + README.md） |

## 注意事项

- tinytoml 是 header-only C++11 库，无二进制产物
- tarball 来自 GitHub tag "0.4"（非 "0.4.0"），版本号映射为 0.4.0
- _promote_nested_source 会丢失同级目录（如 include/），需手动恢复
- CMake 4.x 需要 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 兼容旧 cmake_minimum_required
---

**编译结束**: 2026-06-25 12:04
**功能测试**: 2026-06-25 14:30 — 76/76 PASS (100%)
**最终状态**: published
