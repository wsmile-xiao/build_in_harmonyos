# Encode::HanExtra

## 简介

Encode::HanExtra 是 Perl Encode 模块的扩展，提供额外的中文编码支持，包括：

- Big5-1984, Big5-2003, Big5Ext, Big5Plus
- CCCII (中文信息交换码)
- CNS11643-1 到 CNS11643-7, CNS11643-F
- EUC-TW
- GB18030
- Unisys SOSI1/SOSI2

## 版本信息

- 当前版本: 0.23
- 发布日期: 2007-11-10
- 许可证: MIT

## OHOS 适配状态

### 功能验证 ✅

| 检查项 | 结果 |
|--------|------|
| 编译状态 | 成功 |
| ELF 结构 | ELF64 AArch64 ✅ |
| 编码表完整性 | 21 种中文编码 ✅ |
| 模块结构 | HanExtra.pm + SOSI.pm ✅ |
| 动态链接 | 仅依赖 libc.so ✅ |

### 平台限制 ⚠️

**SELinux 标签限制**：
- 用户路径 `.so` 标签: `hmdfs:s0`（不可加载）
- 系统路径 `.so` 标签: `hnp_file:s0`（可加载）

**解决方案**：安装到系统 Perl 目录：
```
/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/
```

### 与系统 Encode 对比

系统 Encode 模块仅支持基本中文编码（big5-eten, big5-hkscs, gb2312），
HanExtra 补充了台湾标准（CNS）、Big5 变体和更多历史编码。

## 编译注意事项

### Perl XS 模块特殊处理

1. 需要使用 `-I .` 添加当前目录到 Perl @INC，让 inc::Module::Install 可找到
2. CCFLAGS 需要包含 Perl CORE 头文件路径
3. LDDLFLAGS 需要使用 `-shared -nostdlib` 参数

### 编译命令

```bash
perl -I . Makefile.PL PREFIX=$DEFAULT_PREFIX \
  CCFLAGS="-D_GNU_SOURCE -I$DEFAULT_PREFIX/include" \
  LDFLAGS="-L$DEFAULT_PREFIX/lib"

make LDDLFLAGS="-shared -nostdlib -B$DEFAULT_PREFIX/lib -L$DEFAULT_PREFIX/lib -lc"
```

## 依赖

- Perl 5.42.0+
- Encode 模块（核心模块）
- enc2xs 工具（Encode 工具）

## 知识参考

- E097: Perl XS 模块 SELinux 限制
- E112: Perl XS 编译参数
- E113: SELinux 共享库标签限制
