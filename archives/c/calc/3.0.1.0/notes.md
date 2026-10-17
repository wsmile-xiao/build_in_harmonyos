# calc 3.0.1.0 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，无 configure 脚本）
- 编译日期: 2026-09-21
- 编译器: clang 15 (OHOS aarch64, profile: ci/conan/profiles/ohos-aarch64)
- 状态: built

## 编译步骤

### 1. 初始化
官方源码: https://codeload.github.com/lcn2/calc/tar.gz/refs/tags/v3.0.1.0
SHA-256: 7e8f24bb4935b9df51776813364b8e57ec3e1dc694bc8a3d889868f44f2c49e7

### 2. 依赖
readline 为可选依赖（交互式命令行历史），OHOS 环境未安装时自动以
USE_READLINE= READLINE_EXTRAS= 构建无 readline 支持版本。

### 3. 编译
calc 是纯 Makefile 项目，上游明确说明不支持并行编译:
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
配方内部: make -j1 target=Linux CC=<clang> LCC=<clang> LN=cp
             calc-static-only BLD_TYPE=calc-static-only

### 4. 上游测试
- 入口: make check ≡ ./calc -d -q read regress
- 驱动: cal/regress.cal (11031 行) + read 载入 23 个子测试脚本
- 结果: 5782/5782 通过 (100%)，exit_code=0，无失败
- 双口径: source_declared_total=5782, configured_executable_total=5782,
          executed_passed_total=5782, failed=0, unrun=0

### 5. 鸿蒙专项测试
- test_package/test_fpos.cal: 文件位置跟踪（fopen/fputs/rewind/ftell/fseek/fclose）
  13/13 断言通过，TEST_FPOS_PASSED

### 6. 消费者验证
- .logs/consumer/calc_consumer.sh: 复利本息业务计算场景
  仅通过已安装 calc 二进制公开 CLI，校验任意精度数值、正收益合理性
  CONSUMER_PASSED (exit 0)

## 与 2.15.1.0 差异
- 上游 v3.0.1.0 已移除 have_fgetsetpos.c 与 file.h 的 fpos_t 用法
  （2.15.1.0 需 0001/0002 两个 fpos 补丁，3.0.1.0 不需要）
- 配方结构、构建参数、测试结构保持一致
---

**编译结束**: 2026-09-21 15:54
**最终状态**: built
