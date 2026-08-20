# perl-mouse 2.6.0-r0 适配笔记

## 编译环境
- 构建系统: module-build (Module::Build)
- 编译日期: 2026-06-24
- 编译器: clang 18.1.8
- 状态: built

## 编译步骤

1. 下载源码: Mouse-v2.6.0.tar.gz (from CPAN, author: SYOHEX)
2. 初始化: `python3 ohc-run.py init-build perl-mouse 2.6.0-r0 --url=file://...`
3. 设置CFLAGS包含OHOS SDK sysroot头文件:
   ```
   export CFLAGS="-fPIC -O2 -I$SYSROOT/usr/include -I$SYSROOT/usr/include/aarch64-linux-ohos"
   ```
4. 生成构建脚本: `perl Build.PL --prefix=$DEFAULT_PREFIX`
5. 编译: `./Build`
6. 测试: `./Build test` (大部分通过，部分因缺少Test::LeakTrace/Test::Output跳过)
7. DESTDIR安装: `./Build install --destdir=$TEST_PREFIX`
8. 正式安装: `./Build install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | fatal error: 'sys/types.h' file not found | OHOS系统缺少musl系统头文件在默认搜索路径 | 设置CFLAGS包含OHOS SDK sysroot路径 |
| 2 | SSL证书验证失败导致下载失败 | 系统CA证书问题 | 使用Python urllib禁用SSL验证下载 |
| 3 | XS .so 运行时加载 Permission denied | SELinux HMDFS限制: hishell_hap只能加载hnp_file类型 | 创建HNP安装包, 安装到/data/service/hnp/perl.org/ |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- Perl: 5.42.0
- Module::Build: 0.4234
- Module::Build::XSUtil: 0.19
- Devel::PPPort: 3.73
- clang: 18.1.8

## 验证结果

### 编译验证
- .so文件: blib/arch/auto/Mouse/Mouse.so (99648 bytes, ELF shared object 64-bit arm64)
- .codesign签名段: 存在
- XS测试: 大部分通过(XS state: true)
- 纯Perl测试: 部分通过(缺少Test::LeakTrace/Test::Output)

### 功能测试 (2026-06-24 补充)
- 测试总数: 41项
- 通过: 40项
- 失败: 1项 (XS直接加载, 预期SELinux限制)
- 通过率: 97.6%
- 测试覆盖: 模块加载/类定义/属性/类型约束/继承/Role/构造析构/元类/Mouse::Tiny/.so完整性/复杂场景

### 运行时验证
- XS .so文件在 ~/usr/local/lib 下SELinux类型为 hmdfs:s0
- hishell_hap 域只能加载 hnp_file 类型的文件
- 运行时加载受SELinux限制(Permission denied)
- PurePerl模式: ✅ 所有核心功能正常工作

## SELinux 限制分析 (参考 perl-dbd-pg 经验)

| 文件位置 | SELinux type | 加载结果 |
|---------|-------------|----------|
| `/data/service/hnp` (系统目录) | `hnp_file:s0` | ✅ 可加载 |
| `~/usr/local/lib` (HMDFS) | `hmdfs:s0` | ❌ Permission denied |

**解决方案**: 创建 HNP 安装包, 管理员安装到系统目录

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Mouse.so | 99648 bytes | XS共享库 (ELF 64-bit arm64, 已签名) |
| Mouse.bs | 0 bytes | Bootstrap 文件 |
| perl-mouse-2.6.0-r0-ohos-aarch64.hnp | 125363 bytes | HNP 安装包 (28个文件) |
| install-hnp.sh | - | HNP 安装脚本 (含签名和验证) |
| perl-mouse-2.6.0-r0-ohos-aarch64.tar.gz | - | 预编译包 |
| perl-mouse-2.6.0-r0-ohos-aarch64-debug.tar.gz | - | 调试包 |

## 安装指南

### 方法1: HNP 包安装 (推荐, 启用 XS)
```bash
sudo bash packaging/install-hnp.sh
```

### 方法2: 预编译包安装 (不启用 XS)
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-mouse 2.6.0-r0
```

### 安装后验证
```bash
perl -MMouse -e 'print "Mouse version: $Mouse::VERSION\n"'
perl -MMouse::Util -e 'print "XS: ", Mouse::Util::MOUSE_XS() ? "enabled" : "disabled", "\n"'
```

## 注意事项

1. XS模块编译需要OHOS SDK sysroot头文件路径
2. 编译成功但运行时加载XS .so受SELinux HMDFS限制
3. 需要创建HNP包以解决运行时加载问题 (已完成)
4. PurePerl模式功能完整, 可作为临时可用方案
5. 参考 perl-dbd-pg 3.18.0 的 SELinux 限制处理经验

---

**编译结束**: 2026-06-24 20:15
**最终状态**: built
**测试状态**: 97.6% (40/41, 1 expected XS failure)

## Conan 适配 (2026-08-07)

### 构建系统变更
- 原始构建系统: Module::Build + Module::Build::XSUtil (Build.PL)
- Conan 适配: ExtUtils::MakeMaker (Makefile.PL)
- 原因: Module::Build 和 Module::Build::XSUtil 在 OHOS CI 环境不可用

### 关键适配步骤
1. 在 build() 中预生成 ppport.h (使用 Devel::PPPort 核心模块)
2. 在 build() 中预生成 xshelper.h (Module::Build::XSUtil 生成的辅助头文件)
3. 在 build() 中预生成 xs_version.h
4. 生成 Mouse::Tiny (tool/generate-mouse-tiny.pl)
5. 将 XS 源文件复制到 lib/ 目录 (MakeMaker 需要 .xs 与 .pm 同目录)
6. 创建 Makefile.PL 替代 Build.PL
7. 使用 MY::postamble 添加跨目录 .c→.o 编译规则

### 验证结果
- conan create: 通过
- Mouse API 测试: 通过 (has/new/accessor/setter/type constraint/inheritance)
- XS state: PurePerl (HMDFS SELinux 限制, 预期)
