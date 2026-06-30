# libopensmtpd

## 简介
libopensmtpd 是 OpenSMTPD 的库，提供电子邮件处理功能。

## OHOS 适配
- Makefile.gnu 构建（自定义 Makefile）
- 0.1 版本编译成功
- 需要手动编译依赖 libevent 2.1.12

## 关键问题
- **缺少 libevent**: 需要手动编译安装
  - 解决方案: 从 GitHub 克隆 libevent 2.1.12-stable，禁用 OpenSSL 后编译
- **缺少 sys/tree.h**: Makefile 未正确包含 openbsd-compat 目录
  - 解决方案: 在 CFLAGS 中添加 -I.../openbsd-compat
- **链接错误**: 链接器尝试创建可执行文件而不是共享库
  - 解决方案: LDFLAGS 中添加 -shared -Wl,-soname=libopensmtpd.so.0

## 依赖
- libevent 2.1.12-stable（需手动编译）

## 功能验证
```bash
# 检查库
ls -la $HOME/usr/local/lib64/libopensmtpd.so*
```

## 参考
- 主页: https://github.com/murty2/libopensmtpd