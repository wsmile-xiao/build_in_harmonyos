# lrzip — OpenHarmony 编译记录

## 基本信息
- 软件: lrzip
- 描述: 大文件压缩工具，结合多种压缩算法（rzip + lzma/zpaq等）实现高压缩率
- 构建系统: autotools
- 目标: ohos-aarch64
- 最新版本: 0.651

## 已编译版本

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|----------|----------|
| 0.651 | published | 2026-06-12 | lrzip-0.651-ohos-aarch64.tar.gz |

## 依赖

- zlib (压缩支持)
- bzip2 (压缩支持)
- lzo2 (压缩支持)
- lz4 (压缩支持)

## 编译指导

autotools 构建系统，标准流程：
```bash
autoreconf -if
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

注意事项：
1. GitHub tarball 不含 configure 脚本，需先 autoreconf
2. 需设置 PERL5LIB 指向正确的 automake 模块路径
3. HMDFS 文件系统限制临时目录创建，需使用本地 TMPDIR

## 功能验证

```bash
lrzip --version
# 输出: lrzip version 0.651

lrzip -h
# 显示帮助信息
```

## 已知限制

- 无实际测试用例（make check 无内容）