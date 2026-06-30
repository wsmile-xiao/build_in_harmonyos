# bowtie2

**简介**: 快速灵敏的带间隔读段比对工具，用于测序数据比对

**主页**: https://bowtie2.sourceforge.net/

**许可证**: GPL-3.0-or-later

**分类**: data（生物信息数据处理）

## OHOS 适配要点

### 关键适配点
- bowtie2 使用纯 Makefile（非 autotools），无 configure 脚本
- 在 aarch64 上，SSE2 内联函数通过 SIMD Everywhere（simde/x86/sse2.h）实现可移植 SIMD
- Release tarball 不包含 git submodule 内容，需单独下载并填充 third_party/simde 目录
- `uname` 在 OHOS 返回 "HarmonyOS"（非 Linux），Makefile 通过 `uname -m` 正确识别 aarch64
- 无标准 `make check` 目标，使用真实功能验证（建索引+比对）替代
- 包装脚本：`bowtie2`（Perl）、`bowtie2-build`（Python3）、`bowtie2-inspect`（Python3）

### 编译命令
```bash
# 填充 simde submodule（必须先做）
curl -fsSL https://github.com/simd-everywhere/simde-no-tests/archive/refs/heads/master.tar.gz -o /tmp/simde.tar.gz
tar xzf /tmp/simde.tar.gz && rm -rf third_party/simde && cp -a /tmp/simde-no-tests-master third_party/simde

# 编译
make PREFIX=$DEFAULT_PREFIX CXX=clang++ CC=clang -j2
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

### 依赖
- zlib（通过 sysroot 提供）
- pthread（通过 sysroot 提供）
- simde（git submodule，需手动填充）

### 已知问题
- Release tarball 中 simde submodule 为空目录，需手动下载填充
- Perl 包装脚本 `bowtie2` 需安装 Perl 才能使用
- G0 clean-verify 无法运行（无 configure 脚本，工具限制）

### 功能验证结果
- 索引构建：✅ 成功（lambda_virus 示例）
- 单端比对：✅ 94.04% 比对率
- 双端比对：✅ 94.97% 比对率
- 紧凑索引查看：✅ 正确输出