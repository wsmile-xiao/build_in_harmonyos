# scythe 0.994-git20141017.20d3cff 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. W0 依赖预检：`zlib/1.3.2` 已在 ohpcd 制品仓存在。
2. 源码下载：`https://github.com/vsbuffalo/scythe/archive/20d3cff7d7f483bd779aff75f861e93708c0a2b5.tar.gz`
3. 本地 OHOS 交叉编译命令：
   `conan create . -pr:h ohos-local -pr:b default --build=missing -nr`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `make test` 目标无法运行 | Makefile 的 `$?` 将 `clean` 传入链接命令 | 在配方中直接编译并运行 `src/tests/tests.c` 的两个断言 |
| 2 | 本机无法执行 OHOS ELF | 当前是 macOS 交叉编译环境 | 使用 `can_run()`，仅在目标环境可运行时执行测试 |
| 3 | CI 中 gzip FASTQ 测试读入 0 条记录 | 测试数据序列长度 25、质量串长度 24 | 将质量串补齐为 25 个字符 |

## 源码修改
无源码补丁。

## 依赖版本
- zlib/1.3.2

## 验证结果
- `conan-verify --profile ohos-local`: 通过
- `conan create . -pr:h ohos-local -pr:b default --build=missing -nr`: 通过
- 上游测试清点：2 个断言，均已在配方中保留
- 新增测试：2 个（`scythe --version`、gzip FASTQ 修剪）
- HarmonyOS 特有测试：1 个（gzip FASTQ 修剪，验证 OHOS 二进制和 zlib 链接）
- 本地交叉编译环境无法执行 OHOS 二进制，运行时测试需远端 OHOS Worker 验证

## 注意事项
- `finish` 的 W3 本地 CI 模拟被仓库既有隐藏状态文件阻塞，与 scythe 配方无关。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 URL 与 SHA256 |
| test_package/ | 消费者测试 |
| manifest.yaml | 版本元数据 |
| notes.md | 本文件 |
---

**编译结束**: 2026-09-22 17:42
**最终状态**: built
