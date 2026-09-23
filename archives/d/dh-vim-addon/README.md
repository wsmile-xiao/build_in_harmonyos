# dh-vim-addon

debhelper 插件：以标准方式打包 Vim/Neovim 插件（addon），兼容 Vim 的 "package"
机制。纯 Perl 实现，零编译。

`dh_vim-addon` 会在软件包构建目录中，把插件的目录软链接到各编辑器对应的
"packpath"（`$VIM/vimfiles/pack/dist-bundle/{start,opt}`、
`$VIMRUNTIME/site/pack/dist-bundle/{start,opt}`），并在插件存在 `doc/` 目录时
调用 `helpztags` 生成帮助标签；同时提供 `vim_addon` 序列插件供
`dh $@ --with vim_addon` 使用。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.6 | built | 2026-09-13 | 纯 Perl 打包型适配，零编译；依赖 debhelper/13.3.4 + dpkg/1.23.7 |

## 安装内容

- `bin/dh_vim-addon` — debhelper 的 dh_* 插件主脚本（Perl CLI）
- `lib/perl5/Debian/Debhelper/Sequence/vim_addon.pm` — dh sequence 插件
  （`dh $@ --with vim_addon` 挂载）
- `share/man/man1/dh-vim-addon.1` — man 页（上游 `debian/rules` 由
  `pod2man --utf8 dh_vim-addon > dh-vim-addon.1` 生成）

## 运行时依赖

上游 `debian/control` 声明：

- `debhelper (>= 10.2.5)` —— 提供 `Debian::Debhelper::Dh_Lib`
- `libdpkg-perl` —— 提供 `Dpkg::Control::Info` / `Dpkg::Version`
- `vim-common` —— 提供 `helpztags` 与 vim 运行时目录

ohpcd 制品仓中 `debhelper/13.3.4` 与 `dpkg/1.23.7` 均已发布，配方按此声明
`requires`。`vim-common` 未在制品仓发布，故不声明（不捎带适配依赖），
`helpztags` 不可用时仅影响含 `doc/` 目录的插件生成帮助标签这一步。

## 平台限制说明

- 完整运行（生成 `${vim-addon:Depends}` 替换变量）需 Debian dpkg 数据库与
  `vim-common`（`helpztags`）；OHOS 沙箱无此环境。
- 核心功能（把插件目录软链接到 Vim/Neovim 的 `packpath`）不依赖 dpkg 数据库，
  可正常使用——消费者测试已实测验证（见 `0.6/test_package/`）。
