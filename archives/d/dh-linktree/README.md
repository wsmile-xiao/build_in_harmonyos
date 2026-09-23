# dh-linktree

debhelper 插件：在包构建目录中创建符号链接树，用于把嵌入式拷贝（JavaScript/PHP 等解释型语言库）替换为指向系统包文件的符号链接。纯 Perl 实现，零编译。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.9 | built | 2026-09-10 | 纯 Perl 打包型适配，零编译；依赖 debhelper/13.3.4 + dpkg/1.23.7 |

## 安装内容

- `bin/dh_linktree` — debhelper 的 dh_* 插件主脚本
- `lib/perl5/Debian/Debhelper/Sequence/linktree.pm` — dh sequence 插件（`dh $@ --with linktree` 挂载）
- `share/man/man1/dh_linktree.1` — man 页

## 平台限制说明

- 运行时依赖 `Debian::Debhelper::Dh_Lib`（debhelper 包）与 `Dpkg::IPC`/`dpkg`/`dpkg-query`（dpkg 包），两个依赖均已发布 ohpcd
- 完整运行（生成 `${misc:Depends}` 依赖）需 Debian dpkg 数据库；OHOS 沙箱无此环境，符号链接树创建功能可正常使用
