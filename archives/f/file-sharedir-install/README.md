# file-sharedir-install

[File::ShareDir::Install](https://metacpan.org/pod/File::ShareDir::Install) —
让 `Makefile.PL` 能**声明并安装共享数据文件**（Perl）。

## 简介

`File::ShareDir` 让模块在运行时读取随包安装的数据文件（模板、字典、静态资源等），
但「怎么把这些文件装进 `auto/share/...`」原本需要手写 Makefile 规则。
本模块把那部分变成一行声明：

```perl
# Makefile.PL
use ExtUtils::MakeMaker;
use File::ShareDir::Install;

install_share 'share';                                  # dist 级 → auto/share/dist/<DISTNAME>/
install_share module => 'My::Module' => 'my-share';     # 模块级 → auto/share/module/My-Module/

WriteMakefile(NAME => 'My::Module', ...);

package MY;
use File::ShareDir::Install qw(postamble);              # 注入复制规则
```

| 符号 | 导出方式 | 说明 |
|------|---------|------|
| `install_share` | `@EXPORT` | 登记待安装的共享目录（`dist` / `module` 两类，可传目录列表）|
| `delete_share` | `@EXPORT` | 登记待删除的共享路径（`make` 时 `RM_RF`）|
| `postamble` | `@EXPORT_OK` | 在 `package MY;` 段调用，把规则注入生成的 Makefile |

默认**排除隐藏文件与隐藏目录**（`.` 开头）；可用
`$File::ShareDir::Install::INCLUDE_DOTFILES = 1` /
`$INCLUDE_DOTDIRS = 1` 分别开启。

> ⚠️ 本模块是普通 `Exporter` 模块，用编译期 `use` 导入即可；这与
> `Test::*` 系（`Test::Builder::Module` 子类，`use Foo qw(x)` 的参数会被当成
> plan）的导入写法不同。

## OHOS 适配

- **纯 Perl 模块**：无 XS、无 C/C++ 编译、无平台相关代码；运行时依赖
  `Carp` / `Exporter` / `File::Spec` / `IO::Dir` / `strict` / `warnings`
  全为 perl 核心模块，OHOS 行为与上游一致。
- **构建系统沿用上游**：本发行版**自带 `Makefile.PL`**（由 Dist::Zilla 生成，
  直接 `use ExtUtils::MakeMaker`），**不需要**像 Module::Build 系那样生成替代
  构建脚本。配方对「源码根目录缺 Makefile.PL」显式报错，避免上游换构建系统时
  静默出错。
- **零补丁**：未改动任何上游文件，`patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）。模块位于 `<site>/File/ShareDir/Install.pm`，site 根
  需按模块相对路径**上溯两级**；`package_info()` 注入 `PERL5LIB`。

> ⚠️ **测试必须走 `make test`**：`t/10_makefile.t`、`t/11_dotfile.t`、
> `t/12_delete.t` 都以 `plan skip_all if not -f 'Makefile'` 开头并会递归调用
> `make`。改用裸 `prove -Ilib t/` 会让这三个文件静默 skip（用例数从 39 掉到 1）
> 却仍报 "All tests successful" —— 那是假绿。

## 依赖

运行时：`Carp` / `Exporter` / `File::Spec` / `IO::Dir`（perl 核心）；
构建：`ExtUtils::MakeMaker`（perl 核心）；测试：`File::Path` / `Test::More`
（perl 核心）。无 Conan 依赖。

## 功能验证

```bash
# 上游测试套件（4 文件 39 用例）——必须用 make test
cd File-ShareDir-Install-0.14 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=4, Tests=39, Result: PASS

# 消费者验证（conan create 内 test_package，13 条断言）
conan create archives/f/file-sharedir-install/0.14 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 文档: https://metacpan.org/pod/File::ShareDir::Install
- 发行版: https://metacpan.org/dist/File-ShareDir-Install
- 源码: https://cpan.metacpan.org/authors/id/E/ET/ETHER/File-ShareDir-Install-0.14.tar.gz
