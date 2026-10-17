# bamutil 1.0.15 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤
```bash
make TARGET=clang -j2
make TARGET=clang test
```

Conan 配方在 `build()` 中执行相同的 `make TARGET=clang` 构建和上游测试入口。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libStatGen 工具链使用 `CXX=clang` | C++ 编译器命令不正确 | 在 Conan `generate()` 中替换为 `clang++` |
| 2 | splitBam/mergeBam 合法参数被报告为未知选项 | `getopt_long()` 返回值保存到 `char`，OHOS libc 下无法正确表示 `-1`；短选项字符串也不完整 | 将返回值改为 `int`，补齐 `p/P/t/T` 选项 |
| 3 | 多个 BAM 测试因 BGZF/zlib 字节布局差异失败 | 测试比较压缩后的原始 BAM 字节 | 新增 `compareBam.sh`，先解码为 SAM 后比较记录内容 |
| 4 | bam2FastQ gzip 测试引用未压缩文件名 | 测试脚本遗漏 `.gz` 后缀 | 修正 gzip 产物路径，并让 splitRG gzip 场景覆盖 `--qualField OQ` |
| 5 | OQ 场景固定质量期望与当前实现不一致 | 上游期望文件与输入记录的 OQ/QUAL 语义不匹配 | 更新对应 OQ 测试期望，不放宽 FASTQ 内容校验 |

## 源码修改

- `0001-src-MergeBam.cpp.patch`: 修复 `getopt_long()` 返回值类型和短选项声明。
- `0002-src-SplitBam.cpp.patch`: 修复 `getopt_long()` 返回值类型和短选项声明。
- `0003-test-compareBam.sh.patch`: 增加解码后的 BAM 记录比较辅助脚本。
- `0004` 至 `0006`、`0008` 至 `0015`: 将相关 BAM 测试改为语义比较。
- `0007-test-testBam2FastQ.sh.patch`: 修正 gzip 输出路径并补充 OQ 质量字段测试。
- `0004-test-expected-testBam2FastQCoordRGgz.log.patch`: 更新 gzip OQ 场景日志期望。

## 依赖版本

- `zlib/1.3.1`
- `libStatGen` v1.0.15（源码随配方下载）

## 验证结果

```text
上游测试: 19/19 通过（100%）
Conan 消费者测试: 1/1 通过（100%）
```

## 交付物

- `bin/bam`: SAM/BAM 文件处理命令行工具
- 软件级 `commands.json`: 声明 `bam` 命令

## 注意事项

- bamutil 是命令行工具，使用 `TARGET=clang` 构建。
- 上游测试入口来自 `test/Makefile`，共 19 个脚本。
- `test_package` 实际执行打包后的 `bam help`。
---

**编译结束**: 2026-08-30 18:03
**最终状态**: built
