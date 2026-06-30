# perl-module-build-tiny 0.052 适配笔记

## 编译环境
- 构建系统: perl-build (Module::Build::Tiny 自身)
- 编译日期: 2026-06-18
- 编译器: clang/clang++ (不涉及 C 编译，纯 Perl 模块)
- Perl 版本: 5.42.0
- 架构: aarch64-linux
- 状态: built

## 编译步骤

1. **下载源码**: 从 CPAN 获取 Module-Build-Tiny-0.052.tar.gz
2. **解压**: tar xzf Module-Build-Tiny-0.052.tar.gz
3. **配置**: `perl Build.PL` — 生成 Build 脚本
4. **构建**: `perl Build` — 复制模块文件到 blib/
5. **测试**: `perl Build test` — 运行测试套件
6. **安装**: `perl Build install` — 安装到 ~/usr/local/lib/site_perl/5.42.0/
7. **打包**: `ohc-run.py package perl-module-build-tiny 0.052` — 生成预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2 个测试失败: "pm file in blib is readonly" 和 "script in blib is readonly" | OpenHarmony SELinux 限制 chmod 无法设置 readonly (E046)，实际 chmod 后 mode 固定为 660 | 平台限制，不影响模块功能。测试验证构建、安装、加载均正常 |
| 2 | ld.lld 警告: unknown argument '-fstack-protector-strong' | XS 测试中链接器不支持该参数 | 来自 XS 测试而非模块本身，Module::Build::Tiny 是纯 Perl 模块无 XS 组件 |
| 3 | DESTDIR install 失败: "Can't create /data/service/hnp/..." | Module::Build::Tiny 使用 Perl 默认安装路径 (/data/service/hnp/)，该路径为系统目录不可写 | 使用 `perl Build install` 直接安装到 ~/usr/local，或通过 cmd-pkgs 预编译包安装 |

## 源码修改

无补丁。Module::Build::Tiny 是纯 Perl 模块，无需任何源码修改即可在 OpenHarmony 平台上编译和使用。

## 依赖版本

| 依赖 | 版本 |
|------|------|
| perl | 5.42.0 |
| ExtUtils::Config | 0.010 |
| ExtUtils::Helpers | 0.027 |
| ExtUtils::InstallPaths | 0.015 |

## 验证结果

```bash
# 模块加载验证
$ perl -MModule::Build::Tiny -e 'print "Version: $Module::Build::Tiny::VERSION\n"'
Version: 0.052

# 安装位置
$ perl -MModule::Build::Tiny -e 'print $INC{"Module/Build/Tiny.pm"}, "\n"'
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/Module/Build/Tiny.pm

# 构建功能验证
$ perl Build.PL && perl Build && perl Build test
Creating new 'Build' script for 'Hello' version '0.01'
cp lib/Hello.pm blib/lib/Hello.pm
t/basic.t .. ok
All tests successful.
Result: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-build-tiny-0.052-ohos-aarch64.tar.gz | ~19KB | 预编译包 |

## 注意事项

1. **纯 Perl 模块**: Module::Build::Tiny 无 XS/C 组件，不受 SELinux HMDFS 限制影响（与 perl-dbd-pg 的 XS 模块不同）
2. **chmod 限制**: 平台 E046 限制导致 2 个 readonly 测试失败，不影响实际功能
3. **安装路径**: 通过 cmd-pkgs 安装到 ~/usr/local，不依赖系统目录 /data/service/hnp/
---

**编译结束**: 2026-06-22
**最终状态**: built
