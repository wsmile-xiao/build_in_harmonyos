# libptytty

## 简介

libptytty 是一个用于处理 PTY（伪终端）和 TTY（终端）的库，主要用于终端模拟器程序。

## OHOS 适配

### 关键问题

1. **utmpx API 缺失**：鸿蒙系统不支持 utmp/wtmp/lastlog 相关的 API（`setutxent`、`getutxid`、`pututxline`、`endutxent`），必须禁用相关功能。

2. **编译选项**：
   - `-DUTMP_SUPPORT=OFF`
   - `-DWTMP_SUPPORT=OFF`
   - `-DLASTLOG_SUPPORT=OFF`

3. **静态库建议**：建议编译为静态库（`-DBUILD_SHARED_LIBS=OFF`），避免 ELF 签名问题。

4. **链接问题**：C 程序链接 C++ 库时需要显式链接 C++ 标准库（`-lc++`）。

### 与 Linux 的差异

- Linux：完整支持 utmp/wtmp/lastlog 功能
- OHOS：不支持，需要禁用

## 依赖

无外部依赖。

## 功能验证

```bash
# 检查库是否安装
ls ~/usr/local/lib/libptytty.a

# 检查头文件
ls ~/usr/local/include/libptytty.h

# pkg-config 验证
pkg-config --modversion libptytty
```

## 参考

- 源码仓库：https://github.com/yusiwen/libptytty