# liblksctp 1.0.17 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

本次重编译 liblksctp 1.0.17，主要步骤：
1. 使用已有的源码包（已下载并解压）
2. 应用 config.guess/config.sub 补丁（E007 知识）
3. 执行 `./configure --prefix=/storage/Users/currentUser/usr/local`
4. 执行 `make -j1`
5. 执行 `make install DESTDIR=/storage/Users/currentUser/test-install-liblksctp-1.0.17`
6. 制作预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版 config.guess（2015-01-01）不支持 HarmonyOS | 使用 patch-autotools-ohos.pl 补丁脚本（E007 知识） |
| 2 | manifest.yaml configure_options 格式问题 | 空列表 `[]` 被解析为主机类型参数 | 改为空字符串格式 |

## 源码修改

应用补丁：
- `0001-bin-config.guess.patch`：添加 HarmonyOS 检测分支
- `0002-bin-config.sub.patch`：添加 linux-ohos 支持

## 依赖版本

无额外依赖（仅需要基础编译工具）

## 验证结果

```bash
# 验证安装文件
ls -la /storage/Users/currentUser/test-install-liblksctp-1.0.17/storage/Users/currentUser/usr/local/bin/
checksctp   sctp_darn   sctp_status   sctp_test   withsctp

ls -la /storage/Users/currentUser/test-install-liblksctp-1.0.17/storage/Users/currentUser/usr/local/lib/
libsctp.a   libsctp.so   libsctp.so.1   libsctp.so.1.0.17

# 预编译包验证
ls -la archives/l/liblksctp/1.0.17/packaging/
liblksctp-1.0.17-ohos-aarch64.tar.gz (1099964 bytes, 约 1.05MB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liblksctp-1.0.17-ohos-aarch64.tar.gz | 1099964 bytes | 预编译包（含库文件和工具） |
| liblksctp-1.0.17-ohos-aarch64-debug.tar.gz | 516706 bytes | 调试符号包 |

## 注意事项

- liblksctp 是 SCTP 协议的用户空间实现，需要内核 SCTP 支持
- 测试套件（make check）可能因缺少内核 SCTP 支持而无法完整运行
- G0 干净构建验证因 SELinux/HMDFS 权限问题（config.status 创建临时文件失败）无法完成
---

**编译结束**: 2026-06-03 14:14
**最终状态**: built
