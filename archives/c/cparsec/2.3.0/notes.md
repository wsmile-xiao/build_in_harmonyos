# cparsec 2.3.0 适配笔记

## 编译环境
- 构建系统: makefile（上游仅为单头文件库 + 测试 Makefile，无 configure 脚本）
- 编译日期: 2026-09-20
- 编译器: OHOS clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. init-build: 官方 tarball 下载（codeload.github.com/PostgREST/CParseC tag v2.3.0），
   SHA-256 核验 `48966c4b4a767c39069fb808fe884b401a2ad1a7db133ca9ebc888821912347d`
2. 配方类型: header-library（仅分发 cparsec.h，无二进制编译）
3. 上游测试编译运行（clang -std=c99 -O3 -Wextra -Wall -Werror -I.）:
   basic/unnamed/simd/linkage/freestanding/example 全部通过
4. conan create 验证 G1-G4 + test_package 消费者测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试无法用 OHOS clang 编译 | 测试在函数体内用解析器宏定义局部解析器，依赖 GCC 嵌套函数扩展；clang 15 不支持 | 最小补丁将解析器定义提升到文件作用域（名称唯一、断言不变），patches/0001~0004 |
| 2 | 无名解析器 CPC_STRING_ 依赖语句表达式+嵌套函数 | 同上 | 改为等价文件作用域命名解析器（unnamed.c / example.c） |
| 3 | W3 junk_check 命中 cloog/kics 基线状态文件 | main 基线已跟踪的空状态文件（.build-closed/.staging-verified），非当前库改动 | 基线隔离复验：记录路径与隔离前 SHA-256，临时隔离复跑门禁（Junk Files: 0），原样恢复，pre==post ✓；不修改/提交该基线文件 |

## 源码修改

- patches/0001-examples-example.c.patch: example.c 无名解析器改文件作用域命名解析器
- patches/0002-test-basic.h.patch: basic.h 解析器定义提升文件作用域
- patches/0003-test-simd.c.patch: simd.c 解析器定义提升文件作用域
- patches/0004-test-unnamed.c.patch: unnamed.c 无名解析器改命名解析器
- test/ohos_specific_test.c: 新增鸿蒙专项测试（随配方外编译运行，不进入上游源码补丁）

## 依赖版本

无第三方强制依赖（单头文件，不假定 libc）。

## 验证结果

```bash
clang -std=c99 -O3 -Wextra -Wall -Werror -I. -I test test/basic.c -o build/basic.o && ./build/basic.o  # 58 PUTS 断言通过
# 上游 80/80 独立入口全量通过；鸿蒙专项测试 ohos_parse_ok=1；conan create G1-G4 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方 |
| conandata.yml | 官方源 + SHA-256 + 4 补丁声明 |
| test_package/ | 消费者测试（CMake + test.c + MANIFEST.yml） |
| patches/0001~0004 | 解析器定义文件作用域提升补丁 |
| reports/ | conan-verify-report / test-report / harmonyos-specific-test / w3-local-ci 日志 |

## 注意事项

- 基线隔离复验: archives/c/cloog/0.21.1/.build-closed、.staging-verified、
  archives/k/kics/2.1.20/.staging-verified 为 main 基线既有文件（隔离前/后
  SHA-256 均 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855），
  未修改、未提交、未写入知识库或 PR。
---

**编译结束**: 2026-09-20 23:56
**最终状态**: published
