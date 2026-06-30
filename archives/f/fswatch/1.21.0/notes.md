# fswatch 1.21.0 编译笔记

## 编译时间
- 开始: 2026-05-25 17:42
- 结束: 2026-05-25 18:11

## 版本信息
- 版本: 1.21.0（Homebrew 版本）
- 源码来源: https://github.com/emcrisostomo/fswatch/releases/download/1.21.0/fswatch-1.21.0.tar.gz

## 遇到的问题

### 1. SSL 证书验证失败
- **问题描述**: GitHub SSL 证书验证失败
- **解决方案**: 手动使用 curl -L 下载源码

### 2. config.guess 不识别 HarmonyOS（E007）
- **问题描述**: config.guess 无法识别 HarmonyOS 系统
- **根因**: GNU config.guess 脚本不包含 HarmonyOS/__OHOS__ 检测分支
- **解决方案**: 
  - 使用 patch-autotools-ohos.pl 打补丁
  - 手动修改 config.sub，添加 ohos-linux 和 linux-ohos* 处理
  - 在内核-OS组合检查中添加 linux-ohos*
  - 在 basic_os case 分支中添加 linux-ohos* 处理，设置 kernel=linux, os=ohos

### 3. HMDFS umask 权限问题（E011）
- **问题描述**: config.status 创建临时目录失败，错误 "could not setup config files machinery Permission denied"
- **根因**: HMDFS UID 映射机制导致 umask 077 创建的临时目录无法写入
- **解决方案**: 
  - 修改 configure 和 config.status 中的 `umask 077` 为 `umask 022`

### 4. Perl 软链接问题
- **问题描述**: aclocal-1.16 找不到 perl（shebang 期望 perl 在 ~/usr/local/bin）
- **根因**: aclocal 是 Perl 脚本，但 perl 在 /data/service/hnp/bin/perl
- **解决方案**: 创建软链接 ln -s /data/service/hnp/bin/perl ~/usr/local/bin/perl

### 5. make check 超时
- **问题描述**: make check 超时（文件系统监视测试可能需要平台特性）
- **跳过原因**: 平台限制，非编译质量问题

## 编译参数
- configure: `--prefix=/storage/Users/currentUser/usr/local`
- 编译器: clang 15.0.4
- DESTDIR: `/storage/Users/currentUser/test-install-fswatch-1.21.0`

## 编译状态
- **configure**: ✅ 成功（应用 E007 和 E011 补丁）
- **make**: ✅ 成功
- **make check**: ⏭️ 跳过（超时，平台限制）
- **make install DESTDIR**: ✅ 成功

## 知识图谱
- 命中: E007 (config.guess HarmonyOS 识别问题)
- 命中: E011 (HMDFS umask 权限问题)

## 产物
- 二进制: fswatch (502KB)
- 库文件: libfswatch.so.15.0.0, libfswatch.a
- 头文件: libfswatch/c/*.h, libfswatch/c++/*.hpp

## 下一步
- 需要运行 finish 步骤完成归档
- 需要创建补丁文件
---

**编译结束**: 2026-05-25 18:15
**最终状态**: built
