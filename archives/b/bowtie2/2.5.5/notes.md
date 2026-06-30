# bowtie2 2.5.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools）
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. 下载源码（Release tag archive）
2. 填充 third_party/simde submodule（从 simde-no-tests 下载）
3. `make PREFIX=$DEFAULT_PREFIX CXX=clang++ CC=clang -j2`
4. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`

无 configure 脚本，直接使用 make 编译。Makefile 自动检测 aarch64 平台：
- `uname -m` → aarch64 → BITS=64, 无 SSE_FLAG, -fopenmp-simd
- `uname` → HarmonyOS → 不添加 -lrt（正确，musl 已包含）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'simde/x86/sse2.h' file not found` | Release tarball 不含 git submodule 内容，third_party/simde 为空目录 | 从 https://github.com/simd-everywhere/simde-no-tests 下载并填充 third_party/simde 目录 |
| 2 | G0 clean-verify 失败（configure 失败） | bowtie2 无 configure 脚本（纯 Makefile 构建），工具限制 | 手动验证通过，创建 hints/build.sh 提供构建指导 |
| 3 | 无 make check 目标 | bowtie2 测试套件依赖 Perl，OHOS 不可用 | 使用真实功能验证替代（建索引+比对+查看） |

## 源码修改

无源码补丁。唯一改动是填充 third_party/simde submodule 内容（非源码修改，属依赖填充）。

## 依赖版本

- zlib: sysroot 提供（ohos-sdk）
- pthread: sysroot 提供
- simde: simde-no-tests master 分支（git submodule 手动填充）

## 验证结果

### 索引构建
```bash
bowtie2-build example/reference/lambda_virus.fa lambda_virus
# 成功生成 6 个 bt2 索引文件
```

### 单端比对
```bash
bowtie2-align-s -x lambda_virus -U reads_1.fq -S test.sam
# 10000 reads; 94.04% overall alignment rate
```

### 双端比对
```bash
bowtie2-align-s -x lambda_virus -1 reads_1.fq -2 reads_2.fq -S test_pe.sam
# 94.97% overall alignment rate
```

### 版本信息
```bash
bowtie2-align-s --version
# version 2.5.5, 64-bit, clang 15.0.4
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bowtie2-2.5.5-ohos-aarch64.tar.gz | 3.7MB | 主包（含 6 个二进制 + 3 个脚本，已 strip + 签名） |
| bowtie2-2.5.5-ohos-aarch64-debug.tar.gz | 18.9MB | 调试符号包 |

## 注意事项

- Release tarball 需手动填充 simde submodule，不可省略
- `bowtie2` Perl 包装脚本需要 Perl 环境；Python3 包装脚本直接可用
- G0 clean-verify 失败是工具限制（无 configure），不影响实际编译质量
- 质量门禁 G1-G4 全部通过

---
**编译结束**: 2026-05-28 11:35
**最终状态**: published