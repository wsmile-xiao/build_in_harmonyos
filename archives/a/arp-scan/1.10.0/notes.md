# arp-scan 1.10.0 — 适配笔记

## 基本信息
- 软件: arp-scan
- 版本: 1.10.0
- 构建系统: autotools (configure + make)
- 上游仓库: https://github.com/royhills/arp-scan
- 源码: GitHub release tarball (含预生成 configure)
- 许可证: GPL-3.0-or-later

## 依赖
- libpcap/1.10.6 (ohpcd conan repo, static)

## OHOS 适配

### 1. config.guess/config.sub 不识别 HarmonyOS (E007)
- 问题: release tarball 中的 config.guess v2022 不识别 HarmonyOS
- 解决: 在 build() 中 in-place patch config.guess 和 config.sub
  - config.guess: 添加 __OHOS__ LIBC 检测 + HarmonyOS case block
  - config.sub: 添加 linux-ohos* / ohos* 到验证列表

### 2. configure umask 077 问题 (E114)
- 问题: HMDFS 文件系统 setgid + umask 077 导致临时目录不可写
- 解决: 使用 patch (0001-configure-umask-fix.patch) 移除 umask 077

### 3. automake 不可用
- 问题: 源码 archive tarball 不含 configure, 需要 autoreconf
- 解决: 使用 release tarball, 包含预生成的 configure/Makefile.in/config.h.in

## 编译配置
- configure: AutotoolsToolchain 自动生成参数
- make: -j1 (R9: HMDFS jobserver fifo EPERM)

## 测试
- smoke test: arp-scan --version (L2 PASS)
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS
- 本地 CI 模拟: setup.sh + build_and_test.sh PASS

## 编译结束
最终状态: built (conan 配方验证通过, 本地 CI 模拟通过)
COMPLETED
