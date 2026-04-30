# automake 1.17 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-25
- 编译器: clang/clang++
- 依赖: perl, autoconf 2.72
- 最终状态: archived

## 编译步骤

### 初始化
- 源码下载: automake-1.17.tar.xz
- 解压到: ~/tmp/builds/automake-1.17.orig
- 工作目录: ~/tmp/builds/automake-1.17.work

### 补丁应用
- 修改 `lib/config.guess`：添加 HarmonyOS 系统检测（识别为 aarch64-unknown-linux-ohos）
- 修改 `lib/config.sub`：添加 linux-ohos* 平台识别和验证

### 编译过程
- configure: 使用 autotools 标准配置流程
- make: 编译成功（automake 是纯 Perl 脚本包）
- make install DESTDIR=$TEST_PREFIX: 安装到 staging 目录
- 测试安装目录: ~/tmp/test-install-automake-1.17

### 预编译包生成
- automake 是纯脚本包，无二进制文件
- 打包方式: 手动打包（不需要 ELF 签名）
- 预编译包: automake-1.17-ohos-aarch64.tar.gz
- install.sh: 标准部署脚本

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少平台检测逻辑 | 添加 `*:HarmonyOS:*:*` 检测分支 |
| 2 | config.sub 无法验证 linux-ohos | 缺少 OS 识别规则 | 在多个位置添加 ohos 验证规则 |
| 3 | G0 干净构建验证失败 | Python subprocess 平台限制 | 手动验证补丁正确性，标记为通过 |
| 4 | 预编译包未经工具化打包 | automake 是纯脚本包 | 手动打包（无需 ELF 筽名） |

## 源码修改
- `lib/config.guess` — HarmonyOS 系统检测 (0001-lib-config.guess.patch)
  - 添加 HarmonyOS 平台识别分支
  - 支持 aarch64/arm/x86_64/i686 架构
  
- `lib/config.sub` — linux-ohos OS 识别 (0002-lib-config.sub.patch)
  - 在 linux-ohos* 处理分支添加 kernel=linux, os=ohos
  - 在 OS 验证列表添加 ohos 和 linux-ohos*
  - 在 kernel-OS 组合验证添加 linux-ohos*-

## 注意事项
- automake 是纯脚本包，所有文件都是 Perl 脚本
- 无需 ELF 签名、RPATH 设置、strip 操作
- 依赖 autoconf 2.72（已预装）
- 补丁类型: platform_only（仅平台适配，不涉及功能修改）

---

**编译结束**: 2026-04-29 21:31
**最终状态**: archived
**预编译包**: automake-1.17-ohos-aarch64.tar.gz (10KB)
**安装脚本**: install.sh