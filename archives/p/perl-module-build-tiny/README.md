# perl-module-build-tiny

## 软件描述

Module::Build::Tiny 是 Module::Build 的轻量级替代方案，用于构建和安装 Perl 模块。
它仅依赖几个最小的 ExtUtils 模块，提供简洁的 `Build.PL` 接口，适用于不需要
Module::Build 全部功能的纯 Perl 模块项目。

## 版本历史

| 版本 | 编译日期 | 状态 | 说明 |
|------|---------|------|------|
| 0.052 | 2026-06-18 | built | 纯 Perl 模块，编译成功，2 个平台限制测试失败 (E046) |

## 使用说明

### 安装

```bash
# 通过 cmd-pkgs 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-build-tiny 0.052
```

### 验证

```bash
perl -MModule::Build::Tiny -e 'print "Version: $Module::Build::Tiny::VERSION\n"'
# 输出: Version: 0.052
```

### 构建模块

```bash
cd Your-Module/
perl Build.PL
./Build
./Build test
./Build install
```

## 平台注意事项

- **chmod 限制 (E046)**: OpenHarmony 平台 SELinux 限制导致 chmod 无法将文件设为 readonly，
  原始测试套件中 2 个 chmod readonly 测试失败，不影响实际构建功能。
- **DESTDIR 安装**: Module::Build::Tiny 的 install 命令使用 Perl 默认安装路径
  (`/data/service/hnp/...`)，该路径为系统目录不可写。用户安装通过 cmd-pkgs 预编译包
  方式进行，安装到 `~/usr/local`。
- **ld.lld 警告**: XS 测试中出现 `-fstack-protector-strong` 不支持的警告，
  来自 XS 测试而非模块本身，Module::Build::Tiny 是纯 Perl 模块无 XS 组件。

## 依赖关系

| 依赖 | 版本 | 类型 |
|------|------|------|
| perl | 5.42.0 | 运行时 |
| ExtUtils::Config | 0.010 | 运行时 |
| ExtUtils::Helpers | 0.027 | 运行时 |
| ExtUtils::InstallPaths | 0.015 | 运行时 |
