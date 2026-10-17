# libmp3lame 3.100 适配笔记

## 软件信息
- 名称: libmp3lame (LAME MP3 Encoder)
- 版本: 3.100
- 构建系统: autotools
- 上游仓库: https://sourceforge.net/projects/lame/
- 源码 URL: https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz
- SHA256: ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e
- 许可证: LGPL

## 依赖
- 无外部库依赖（mpglib 内置解码器）
- 可选: nasm（x86 汇编优化，arm64 不适用）

## 适配修改

### 1. config.guess 补丁 (E007)
- 版本: 2015-03-04（旧版，使用 echo+exit 语法而非 GUESS= 变量）
- 添加 HarmonyOS 系统检测分支
- patch-autotools-ohos.pl 脚本自动添加但使用 GUESS= 格式，需手动改为 echo+exit

### 2. config.sub 补丁 (E007)
- 版本: 2015-03-08
- 添加 ohos-linux 三元组支持（3 处修改）
- 1. ohos-linux) case 块
- 2. maybe_os 列表添加 linux-ohos*
- 3. kernel-os 组合列表添加 -linux-ohos*

### 3. config.status umask 修复
- 问题: config.status 使用 `umask 077` 创建临时目录，鸿蒙安全策略阻止写入
- 修复: `umask 077` → `umask 022`
- 根因: 鸿蒙 SELinux/安全模型限制 umask 077 创建的目录的写入权限

## 编译参数
- `./configure --prefix=$DEFAULT_PREFIX`
- 无额外参数（仅 --prefix，遵循 R1 参数最少化）

## 编译结果
- libmp3lame.so.0.0.0 (动态库)
- libmp3lame.a (静态库)
- lame (前端可执行文件)
- lame.h (头文件)

## 测试
- `lame --version` 输出: LAME 64bits version 3.100
- `make check`: 通过（LAME 无自动化测试套件）
- 安全弹窗: 已触发并通过

## 注意事项
- libmp3lame 包含可执行文件 `lame`，需要 commands.json (R38)
- 源码通过 Debian 镜像下载（SourceForge 被 Cloudflare 403），但 conandata.yml 使用 SourceForge 官方 URL
- config.guess 旧版需要 echo+exit 语法（非 GUESS= 变量）
---

**编译结束**: 2026-08-10 13:19
**最终状态**: built
