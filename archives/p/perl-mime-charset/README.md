# perl-mime-charset

**MIME::Charset** — Perl module providing charset information for MIME.

## 软件描述

MIME::Charset provides functions and object-oriented interface to handle
character set information in MIME-compliant messages. It maps between
charset names (aliases), and provides encoding/decoding helpers for
RFC 2047 encoded words in email headers.

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.013.1 | published | 2026-06-17 | 纯 Perl 模块，无原生二进制 |

## 使用说明

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-mime-charset 1.013.1

# 验证
perl -MMIME::Charset -e 'print $MIME::Charset::VERSION, "\n"'
```

## 依赖

- **Perl**: >= 5.42.0
- **Encode**: >= 1.98 (核心模块，已满足)

## 许可证

Artistic-2.0 (Perl 标准许可证)
