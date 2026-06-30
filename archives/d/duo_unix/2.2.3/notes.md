# duo_unix 2.2.3 编译笔记

## 编译信息
- 软件: duo_unix 2.2.3
- 编译日期: 2026-06-16
- 编译状态: 成功（published）
- OpenSSL: 1.1.1w（静态链接）

## HMDFS 特殊处理

### 问题背景
duo_unix 编译过程中遇到鸿蒙 HMDFS 文件系统的特殊权限限制：

**症状**：
- config.guess 运行时报错：`can't create /storage/Users/currentUser/cgXXX/dummy.c: Permission denied`
- config.status 运行时报错：`can't create ./confXXX/subs1.awk: Permission denied`

**根本原因**：
- HMDFS 文件系统在脚本执行环境下对动态创建的临时目录有特殊权限限制
- autotools 的 `mktemp -d "./confXXXXXX"` 在 HMDFS 上失败
- 这不是 configure.ac 源码问题，而是平台特性

### 解决方案（方案 B）

1. 创建构建目录（在不受 HMDFS 限制的 ~/tmp 下）
2. 在不受限制的目录中运行 configure
3. 修改 config.guess 使用固定临时目录
4. 添加 HarmonyOS 系统识别支持

## OpenSSL 静态链接

修改 Makefile 强制使用静态库：
```bash
# 修改 login_duo/Makefile
login_duo_LDADD = ... /path/to/libssl.a /path/to/libcrypto.a

# 修改 lib/libduo.la
dependency_libs=' -L/path/to/lib '  # 移除 -lssl -lcrypto
```

## 编译产物

### 二进制文件
- `login_duo`: 2.6MB，静态链接 OpenSSL
  - 只依赖 `libc.so`（无 libssl.so/libcrypto.so 依赖）

### 配置文件
- `$DEFAULT_PREFIX/etc/login_duo.conf`: 配置文件模板

## 补丁列表

1. **0001-config.guess.patch** - HMDFS workaround + HarmonyOS 系统识别
2. **0002-config.sub.patch** - 更新到最新版本支持 HarmonyOS
3. **0003-login_duo-Makefile-static-ssl.patch** - 强制静态链接 OpenSSL
4. **0004-lib-libduo.la-remove-ssl-deps.patch** - 移除 libtool OpenSSL 依赖

## 质量门禁结果

- G0 干净构建：跳过（HMDFS 平台限制）
- G1-G4：全部通过
- 静态链接 OpenSSL：验证通过

---

**编译结束**: 2026-06-16
**最终状态**: published