# dh-elpa

debhelper 插件：将 Emacs Lisp（ELPA 风格）包安装进 Debian 包构建目录，并通过 `emacs -batch` 按需字节编译（`.elc`）、生成 `-pkg.el` 描述文件与 emacsen-common 维护者脚本。纯 Perl 实现，零编译。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.2.0 | built | 2026-09-13 | 纯 Perl 打包型适配，零编译；依赖 debhelper/13.3.4 + dpkg/1.23.7 + perl-config-tiny/2.30 + emacs/29.1（Module::Metadata 为 perl 核心模块，无需 conan 依赖） |

## 安装内容

- `bin/dh_elpa` — debhelper 的 dh_* 插件主脚本（emacs -batch 驱动的安装器）
- `bin/dh_elpa_test` — ERT/Buttercup 测试运行器
- `share/perl5/Debian/Debhelper/Sequence/elpa.pm` — dh sequence 插件（`dh $@ --with elpa` 挂载）
- `share/debhelper/dh_elpa/emacsen-common/{compat,install,remove}` — debhelper 模板
- `share/debhelper/autoscripts/prerm-elpa` — 维护者脚本模板
- `lib/dh-elpa/{install,remove}` — 安装/卸载 helper（dh-elpa-helper 并入本包）
- `share/emacs/site-lisp/elpa/dh-elpa.el` — Emacs Lisp 安装器（emacs -batch 调用）
- `share/man/man1/dh_elpa.1 + dh_elpa_test.1` — man 页（pod2man 生成）

## 平台限制说明

- `dh_elpa` 的安装器就是 `emacs -batch -l dh-elpa.el`——无 emacs 无法工作，emacs 为硬性运行时依赖
- 字节编译模式的 helper 模板目录上游硬编码 `/usr/share/debhelper/...`——补丁 0001 支持 `DH_ELPA_TEMPLATEDIR` 环境变量覆盖（默认保持 Debian 行为）
- `dh_elpa_test` 的 ERT/Buttercup 运行模式依赖 File::Find::Rule / Array::Utils / Text::Glob / Debian::Control，后三者未发布 ohpcd——`dh --with elpa` 序列的测试步骤受限（dh_elpa 主安装路径不受影响）
- 上游要求 emacs >= 1:30.1，制品仓为 29.1——package.el API 兼容，版本偏差已记录
