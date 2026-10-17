# perl-sereal-decoder

**Sereal::Decoder** — Sereal 二进制反序列化解码器 (Perl XS 模块)。

## 软件信息

- **官网**: https://metacpan.org/dist/Sereal-Decoder
- **源码**: https://cpan.metacpan.org/authors/id/Y/YV/YVES/Sereal-Decoder-5.004.tar.gz
- **许可证**: perl_5 (Artistic or GPL)
- **分类**: serialization

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 5.004-r3.1 | published | 2026-06-30 | XS 模块编译成功，ELF 已签名 |

## 构建系统

Perl ExtUtils::MakeMaker (Makefile.PL) — XS(C) 模块，需要 C 编译器。

内嵌依赖: miniz, csnappy, zstd (静态编译进 .so，无外部 C 依赖)。

## 编译依赖

- perl 5.42.0
- clang 15 (OHOS 工具链)
- Conan 2.29.1 (OHOS 适配版)

## 运行依赖

- perl 5.42.0

## 使用说明

```bash
# Install via Conan
conan install --requires=perl-sereal-decoder/5.004-r3.1@ohpcd/stable

# Use in Perl
perl -e 'use Sereal::Decoder; my $dec = Sereal::Decoder->new(); my $data = $dec->decode($binary);'
```

### 产物

| 文件 | 大小 | 说明 |
|------|------|------|
| Decoder.so | 264KB | XS 共享库 (ELF aarch64, self-signed) |
| Decoder.pm | 33KB | Perl 模块主文件 |
| Constants.pm | 44KB | 常量定义模块 |
| Performance.pm | 10KB | 性能调优模块 |

## 注意事项

- .so runtime 加载在 HMDFS 上受 SELinux 限制 (E046)，需安装到系统 Perl 路径后使用
- ELF 签名 (binary-sign-tool -selfSign) 已集成到 conanfile.py package() 方法
- test_package 使用文件验证 + 语法检查模式，不做 runtime .so 加载
- 详见 `5.004-r3.1/notes.md` for detailed adaptation notes

---
*OpenHarmony 编译归档 · 初次编译: 2026-06-30, 更新: 2026-07-01*
