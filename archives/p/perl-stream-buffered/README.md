# perl-stream-buffered

Stream::Buffered - temporary buffer to save bytes (Pure Perl module)

## 软件信息

- **官网**: https://metacpan.org/dist/Stream-Buffered
- **源码**: https://cpan.metacpan.org/authors/id/D/DO/DOY/Stream-Buffered-0.03.tar.gz
- **许可证**: perl_5 (Artistic License 1.0 或 GPL)
- **分类**: perl-module
- **作者**: Tatsuhiko Miyagawa

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.03-r5 | published | 2026-07-03 | 纯 Perl 模块，无需补丁，全部门禁通过 |

## 运行依赖

- perl 5.42.0

## 编译依赖

- perl 5.42.0 (系统自带)
- make

## 使用说明

Stream::Buffered 是一个临时缓冲区模块，用于存储任意长度的字节串并获取可 seek 的文件句柄。
根据数据长度自动选择 PerlIO 或临时文件作为后端。

### API

```perl
use Stream::Buffered;

my $buf = Stream::Buffered->new($length);
$buf->print($bytes);
my $size = $buf->size;
my $fh   = $buf->rewind;
```

- `new($length)`: 创建缓冲区，`$length` 为预期数据大小（数字）
- `print($bytes)`: 向缓冲区写入数据
- `size()`: 返回当前缓冲区大小
- `rewind()`: 返回可读的文件句柄

### 后端选择逻辑

- `$MaxMemoryBufferSize < 0`: 始终使用 PerlIO
- `$MaxMemoryBufferSize == 0`: 始终使用临时文件
- 未指定 `$length`: 使用 Auto（自动切换）
- `$length > $MaxMemoryBufferSize`: 使用临时文件
- 其他: 使用 PerlIO

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-stream-buffered/0.03-r5
```

安装产物路径：
- `lib/Stream/Buffered.pm`
- `lib/Stream/Buffered/Auto.pm`
- `lib/Stream/Buffered/File.pm`
- `lib/Stream/Buffered/PerlIO.pm`

### 注意事项

- 纯 Perl 模块，无 C/XS 扩展，不涉及 CRT 文件或 SELinux/HMDFS 限制
- `new()` 参数应为数字（预期数据长度），不是后端名称字符串
- 该模块是 Plack 项目的一部分，独立发布以便复用

---
*OpenHarmony 编译归档 · 2026-07-03*
