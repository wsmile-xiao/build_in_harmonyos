# genimage 19 — 编译笔记

## 基本信息
- 软件: genimage (Image generation tool for embedded systems)
- 版本: 19
- 构建系统: autotools
- 编译器: clang 15.0.4
- 平台: HarmonyOS aarch64

## 编译过程

### 补丁 (5 个)
1. `0001-build-aux-config.guess.patch` — OHOS 平台识别
2. `0002-build-aux-config.sub.patch` — OHOS 平台识别
3. `0003-config.c.patch` — get_current_dir_name() → getcwd() 替换
4. `0004-configure.patch` — HMDFS config.status 权限修复
5. `0005-genimage.h.patch` — 自定义 offsetof → stddef.h offsetof 替换

### 关键适配
- **HMDFS config.status**: HMDFS 文件系统上新建文件继承父目录 uid，导致 config.status 权限问题，通过使用 TMPDIR 避免
- **get_current_dir_name()**: OHOS 不提供此 glibc 扩展，替换为 POSIX getcwd()
- **offsetof 宏冲突**: genimage.h 的自定义 offsetof 与 clang _Static_assert 不兼容，替换为标准 stddef.h offsetof
- **libtool 语法错误**: HMDFS 上 libtool 脆弱，通过手动链接绕过

### 验证
- `genimage --version` 输出 "19"
- 二进制 ELF 64-bit PIE aarch64

## 适配说明
- genimage 是嵌入式系统镜像生成工具，依赖 libconfuse
- HMDFS 文件系统对 autotools 构建有多个限制（uid 继承、权限问题）
- 需要更新 config.guess/config.sub 以识别 HarmonyOS 平台