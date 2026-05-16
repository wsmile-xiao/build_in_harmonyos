# figlet 2.2.5 for OpenHarmony

**发布日期**: 2026-05-11  
**平台**: OpenHarmony aarch64  
**编译器**: clang 15.0.4

## 简介

figlet 是一个将普通文本转换为大型 ASCII 艺术字符的程序。它可以创建由键盘字符组成的"签名"，广泛用于终端欢迎消息、邮件签名和文档装饰。

## 变更说明

### 编译修复
- 修复 `utf8.h` 中缺少 `#include <sys/cdefs.h>` 导致的编译错误
- 解决 `__BEGIN_DECLS`/`__END_DECLS` 宏未定义问题

### 已知问题
- 编译时产生 22 个 K&R 风格函数原型弃用警告（C2x 标准将不支持，但不影响功能）
- 默认字体路径硬编码为 `/usr/local/share/figlet`，运行时需用 `-d` 参数指定实际路径

## 包含内容

### 可执行文件
- `figlet` - 主程序，将文本转换为 ASCII 艺术
- `chkfont` - 字体文件验证工具
- `figlist` - 列出可用字体
- `showfigfonts` - 显示字体示例

### 字体文件 (18个)
- standard, banner, big, block, bubble, digital, ivrit, lean, mini, mnemonic
- script, shadow, slant, small, smblock, smshadow, term, tlf2

### 手册页
- figlet.6, chkfont.6, figlist.6, showfigfonts.6

## 使用方法

```bash
# 基本使用
figlet -d /path/to/fonts "Hello World"

# 使用不同字体
figlet -d /path/to/fonts -f slant "Hello"

# 查看版本信息
figlet -I 2
```

## 安装

```bash
# 解压安装包
tar -xzf figlet-2.2.5-ohos-aarch64.tar.gz

# 运行安装脚本
./install-figlet-2.2.5.sh
```

## 验证

```bash
# 验证安装
figlet -d /path/to/fonts Test
```

## 文件校验

| 文件 | 大小 |
|------|------|
| figlet-2.2.5-ohos-aarch64.tar.gz | 803KB |
| figlet-2.2.5-ohos-aarch64-debug.tar.gz | 132KB |

## 许可证

MIT License

## 参考资料

- 官方网站: http://www.figlet.org/
- 源码下载: http://www.figlet.org/pub/figlet/program/unix/