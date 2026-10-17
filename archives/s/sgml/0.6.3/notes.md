# notes.md — sgml 0.6.3 (sgml-common) OHOS 适配笔记

## 软件身份
- 名称: sgml / sgml-common 0.6.3（RHEL9 SRPM sgml-common-0.6.3-58.el9 同源包）
- 上游: https://www.sourceware.org/pub/docbook-tools/new-trials/SOURCES/sgml-common-0.6.3.tgz
- sha256: 7dc418c1d361123ffc5e45d61f1b97257940a8eb35d0bfbbc493381cc5b1f959
- 性质: noarch —— 纯 SGML/XML ISO 实体数据、DTD 目录声明与两个 shell 工具
  （install-catalog、sgmlwhich），无编译代码，无第三方依赖（R36 预检 0 依赖）。

## 关键适配点
1. tarball 内 automake 辅助脚本为绝对路径符号链接（→ /usr/share/automake/*）：
   - conan 解包 (fully_trusted) 产生悬空链接；
   - OHOS 无 /usr/bin/install、无宿主 automake → configure (AC_PROG_INSTALL)
     找不到 install 会直接报错，make install 的 $(mkinstalldirs)/$(install_sh) 也会失败。
   - 方案: conanfile.py build() 在 configure 前 unlink 悬空链接并写入自包含的
     install-sh / mkinstalldirs（POSIX sh 实现，仅覆盖本项目 Makefile 用到的
     -c/-m/-d 子集），不引入任何补丁、不依赖环境。
2. COPYING/INSTALL 悬空链接仅出现在 EXTRA_DIST，不参与构建，一并 unlink 以防 dist 类目标误触。
3. configure/make/install 均走 Conan Autotools 工具链（R9: -j1；R33: 不读裸环境变量）。

## 安装产物
bin/install-catalog, bin/sgmlwhich, etc/sgml/sgml.conf, man/man8/install-catalog.8,
share/sgml/{sgml-iso-entities-8879.1986, xml-iso-entities-8879.1986, xml.dcl, stylesheets},
doc/sgml-common-0.6.3/html/ — 已在本机探索构建中用 DESTDIR 安装验证。

## 测试
上游无任何测试（check 目标为空）→ 自写 test_package 消费者测试（6 组检查，
含 install-catalog 目录注册/注销往返），见 test_package/MANIFEST.yml。

## R47 语言预检
lang-preflight: C 语言检出（partial, shell 为主）——conan 配方适用，继续 conan 流水线。
---

**编译结束**: 2026-09-28 17:55
**最终状态**: built
