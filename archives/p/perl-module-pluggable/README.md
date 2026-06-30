# perl-module-pluggable

Module::Pluggable — 为 Perl 模块提供自动插件发现能力。

## 简介

Module::Pluggable 是一个纯 Perl 模块，无需编译任何 C/XS 代码。它通过 `use Module::Pluggable` 导入 `plugins()` 方法，自动在指定搜索路径下发现并加载插件模块。同时提供 `Module::Pluggable::Object` 面向对象接口和 `Devel::InnerPackage` 内部包检测工具。

## 构建信息

| 项目 | 值 |
|------|-----|
| 版本 | 6.3 |
| 构建系统 | ExtUtils::MakeMaker (Makefile.PL) |
| 编译状态 | ✅ published |
| 构建日期 | 2026-06-18 |
| 平台 | OpenHarmony (aarch64-linux) |
| Perl | 5.42.0 |

## 安装

```bash
# 通过 cmd-pkgs 公共安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-pluggable 6.3
```

安装后设置环境变量：
```bash
export PERL5LIB=$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/perl5
```

## 使用示例

```perl
package MyApp;
use Module::Pluggable search_path => "MyApp::Plugin";

my @plugins = MyApp->plugins;
# 返回: MyApp::Plugin::Foo, MyApp::Plugin::Bar, ...
```

## 平台说明

- **纯 Perl 模块**：无二进制代码，无 SELinux/HMDFS 限制问题
- **已知限制**：`t/29unreadable.t` 测试失败（OpenHarmony 不强制 POSIX 文件权限，chmod(0200) 无效），不影响功能
- **SSL 证书**：下载源码时可能遇到 SSL 证书验证失败，使用 `curl --insecure` 解决

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 6.3 | 2026-06-18 | published | 首次编译，45 个测试文件中 44 个通过 |
