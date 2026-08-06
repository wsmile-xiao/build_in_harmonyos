# Data-UUID 1.227 编译笔记

## 编译状态：published

## 适配历史

### 历史编译（2026-06-10）

- 状态：built
- 方案：手动编译，使用 -nostartfiles -nodefaultlibs + musl libc.so 链接
- 问题：缺少 CRT 文件，SELinux HMDFS 限制阻止 .so 加载
- 结果：UUID.so 生成 (25KB)，功能通过静态分析验证

### Conan 适配（2026-08-06）

#### 构建系统
- Perl ExtUtils::MakeMaker (Makefile.PL)
- Perl 5.42.0 位于 /data/service/hnp/bin/perl
- Perl CORE 头文件位于 /data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux/CORE/

#### 构建过程
1. `perl Makefile.PL` → 生成 Makefile
2. `make` → xsubpp 生成 UUID.c → clang 编译 UUID.o → 链接 UUID.so (35KB)
3. `make install INSTALL_BASE=...` → 安装到 staging 目录

#### 适配修改
- **UUID.xs**: 添加 `__OHOS__` 守卫，跳过 `gethostid()` 调用
  - `gethostid()` 在 OHOS 平台不可用（链接时 undefined symbol）
  - 修改 `#  elif !defined(__ANDROID__)` 为 `#  elif !defined(__ANDROID__) && !defined(__OHOS__)`

#### Conan 配方
- 构建系统：custom（Perl MakeMaker）
- 无外部依赖
- 产物：UUID.so + UUID.pm
- test_package：shell 脚本测试 Data::UUID API（create_str, to_string, from_string, compare）

#### 验证结果
- conan-verify G2 (conan create): ✓ PASS
- 本地 CI 模拟 (W3): ✓ PASS
- 运行时测试因 OHOS HMDFS SELinux 限制 (E212) 无法加载 .so

#### 平台限制
- OHOS hmmac 安全模块阻止从 HMDFS 路径 dlopen .so 文件
- 解决方案：通过 cmd-pkgs HNP 包安装到 /data/service/hnp/ 目录

## 结束

最终状态: published — Conan 配方验证通过，CI 模拟通过，审计通过
