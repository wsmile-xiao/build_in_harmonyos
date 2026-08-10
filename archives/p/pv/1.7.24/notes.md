# pv 1.7.24 编译笔记

## 编译时间
- 原始编译: 2026-05-25 16:50-17:08
- Conan 适配: 2026-08-08 02:30-02:45

## 版本信息
- 编译版本: 1.7.24（GitHub 最新稳定版）
- 源码来源: https://github.com/a-j-wood/pv (tag v1.7.24)

## 构建系统
- autotools (autoconf 2.72)
- 源码不含 configure 脚本，需用 autoconf 从 autoconf/configure.in 生成
- 需运行 make make 和 make dep 生成 Makefile 片段和依赖

## 遇到的问题

### 1. HMDFS umask 权限问题 (E011)
- configure 中 umask 077 导致临时目录创建失败
- 修复: sed -i 's/umask 077/umask 022/g' configure (E011 推荐方案)

### 2. make check 失败
- 34/35 测试失败 (Signal 31 core dumped)
- 原因: 平台 syscall 限制
- 影响: 非阻塞，平台限制非编译质量问题

## Conan 适配 (2026-08-08)
- 生成 conanfile.py (application 类型, autotools 构建)
- 生成 conandata.yml (GitHub 官方源 + sha256)
- 生成 test_package/ (VirtualRunEnv + test.sh, R34 合规)
- 生成 commands.json (R38 命令行工具声明)
- 移除 0002-configure.patch (生成文件, R6 合规)
- conan-verify: G2/G3/G4 全部通过
- 本地 CI 模拟 (W3): 通过.

## 编译状态
- configure: ✅ 成功
- make: ✅ 成功
- make install DESTDIR: ✅ 成功
- conan create: ✅ 成功 (G2 PASS)
- conan-verify: ✅ 全部通过
- 最终状态: built (conan-verify 通过, 待 CI upload)
