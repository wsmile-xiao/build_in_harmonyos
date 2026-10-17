# libax25 0.0.12-rc5 适配笔记

## 软件信息
- 名称: libax25
- 版本: 0.0.12-rc5
- 描述: hamradio AX.25/ROSE/NET/ROM 协议函数库
- 构建系统: autotools (configure.ac + Makefile.am)
- 外部依赖: 无（zlib 可选，系统已有）

## 源码来源
- 官方URL: http://www.linux-ax25.org/pub/libax25/libax25-0.0.12-rc5.tar.gz (已下线)
- 实际使用: Debian orig tarball (http://deb.debian.org/debian/pool/main/liba/libax25/libax25_0.0.12-rc5+git20230513+5581005.orig.tar.gz)
- SHA256: 4d0546e79add1c1859871094cb42eafdfb65ba0ddaf6f453b99192cbef6e3a44

## 适配修改

### 1. config.guess/config.sub OHOS 平台识别 (E007)
- 使用 patch-autotools-ohos.pl 脚本打补丁
- config.guess: 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别
- config.sub: 添加 ohos-linux triplet 和 ohos* OS 列表
- 手动修复: 在 config.sub 的 kernel-OS 兼容性检查中添加 `linux-ohos*-` 选项

### 2. HMDFS umask 077 兼容性修复
- 问题: HMDFS 上 mktemp -d 创建的目录 owner 为挂载点 owner，而非当前用户
- umask 077 创建 700 权限目录，当前用户无权限访问
- 修复: 移除 configure/config.status/libtool 中的 umask 077/0077 设置

### 3. autoreconf
- 源码仅有 configure.ac + Makefile.am，需先运行 autoreconf --install --force 生成 configure

## 编译结果
- libax25.so.0.0.0: AArch64 共享库，依赖 libc.so
- libax25io.so.0.0.0: AArch64 共享库，依赖 libz.so + libc.so
- libax25.a / libax25io.a: 静态库
- make check: 无测试目标，返回 0

## 库类型判断
- libax25 是系统同名库（系统可能有 /lib/libax25.so）
- R26: 必须在 generate() 中设置 BUILD_SHARED_LIBS=OFF
- R38: 库类型，不需要 commands.json
---

**编译结束**: 2026-07-17 14:58
**最终状态**: published
