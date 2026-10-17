# debconf 1.5.77 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译，上游 Makefile 仅构建 doc/po 文档）
- **编译日期**: 2026-08-30
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/d/debconf/1.5.77 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 Debian 官方源池下载 tar.xz 并 strip_root
（tar 顶层目录为 work/，strip_root 后即源码根）。

### 2. 打包（package()）
- 纯 Perl 库：`Debconf/**/*.pm`（约 30 个模块）→ `lib/perl5/`
- 可执行脚本（debconf、debconf-* 系列、confmodule 等）→ `bin/`
- debconf.conf → `etc/debconf/`，debconf.py → `lib/`
- package_type=application，无库可链接

## 上游测试（rule 4 全量核验）
- 测试目录：`work/Test/`，Test::Unit 框架套件（AllTests.pm 聚合 CopyDBTest +
  DbDriver 各驱动测试：DirTree/File/LDAP/PackageDir/Common）
- 依赖：Test::Unit::* CPAN 模块 + 真实数据库驱动（LDAP/SLAPD 等）
- **OHOS 沙箱无法运行**（无 Test::Unit CPAN 模块、无 LDAP 环境）——如实记录，
  不伪造通过率（rule 4/5.2）
- 适配后：test_package R34 真实调用 `Debconf::Config` 模块 API（纯 Perl，
  `perl -I<lib> -e 'use Debconf::Config; ...'`），1/1 = 100%

## 已知限制
- 上游 Test::Unit 套件需 CPAN 依赖 + 真实数据库驱动，沙箱无法运行
- debconf 核心为 Perl 模块 + CLI 脚本集合，无编译产物
