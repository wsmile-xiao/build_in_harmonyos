# isync

**IMAP and MailDir mailbox synchronizer (mbsync)**

## 简介

isync (mbsync) 是一个命令行工具，用于在 IMAP 服务器和本地 MailDir 风格邮箱之间同步邮件。它支持：
- 双向同步
- 增量同步
- 多账户配置
- SSL/TLS 加密连接

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.5.1 | built | 2026-05-26 |

## 编译说明

### 依赖
- openssl 1.1.1+
- zlib 1.2+

### 平台适配
- OpenHarmony 需要更新 config.guess/config.sub
- OpenHarmony 缺少 getpass() 函数，已提供替代实现

## 使用方法

```bash
# 配置文件示例
mbsync -c ~/.mbsyncrc

# 同步邮箱
mbsync <账户名>
```

## 项目主页

https://isync.sourceforge.net/