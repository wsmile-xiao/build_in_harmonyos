# alpine-baselayout 3.7.2 适配笔记

## 任务身份

- 平台库名: alpine-baselayout，平台版本: 3.7.2，Issue: #2084
- 上游: Alpine Linux aports 仓库 `main/alpine-baselayout`（v3.23 分支，pkgver=3.7.2 pkgrel=0）
- 归档: archives/a/alpine-baselayout/3.7.2/

## 三重身份

| 身份 | 名称/版本 | 说明 |
|------|-----------|------|
| 平台 | alpine-baselayout 3.7.2 | 任务平台 Issue #2084 指定 |
| 上游 | alpine-baselayout 3.7.2 | Alpine aports v3.23 分支 3.7.2-r0（commit 15b3b78187），与平台一致 |
| 归档 | alpine-baselayout 3.7.2 | Conan name/version 与平台、上游完全一致，无需映射解释 |

## 上游核验

- 上游仓库: https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/alpine-baselayout
- 版本来源: pkgs.alpinelinux.org v3.23 分支 alpine-baselayout 3.7.2-r0，构建 commit 15b3b78187b3808104f98f765e9632e0b09281a7
- 源码获取: 按 APKBUILD source 清单逐文件下载（git.alpinelinux.org plain URL + Debian netbase v6.4），全部 SHA512 与 APKBUILD sha512sums 一致，SHA256 记录于 conandata.yml
- 许可证: GPL-2.0-only（APKBUILD license 字段；官方 GPLv2 文本随包安装）
- 语言: noarch（纯文本配置 + shell 脚本，无源码编译）
- 构建系统: abuild/APKBUILD（自定义，无 configure/make）
- 安装产物: /etc 下配置文件（group/passwd/inittab/profile/protocols/services/shadow/crontabs/modprobe.d/profile.d）+ hier.7 man page

## 路径 A 方案

纯数据/配置包，无编译步骤。按上游 APKBUILD package() 布局把真实配置文件安装到
Conan 包内相对路径（etc/、usr/share/man/man7/），并安装 GPL-2.0 许可证。
**不照搬 Alpine 根文件系统路径**：/dev、/proc、/sys、/bin、/lib、/var、home、root、
media、mnt、opt、srv、run、tmp 等宿主系统目录均不进入包；shadow 由 build()
按上游 awk 语义生成（root 密码字段 '::'，其余 ':!:'，后接 ':0:::::'）。

## 编译步骤

1. 逐文件下载并核验 SHA256（conandata.yml，15 个文件，全部通过）
2. build(): 生成 shadow（复现上游 awk 逻辑）
3. package(): 安装配置到包内相对路径 + licenses/GPL-2.0.txt
4. test_package: test_smoke.sh 真实断言（9 组断言：文件存在、内容标识、shadow 语义、许可证、sh -n）
5. conan create / conan-verify / finish built

## 上游测试

上游 APKBUILD `options="!fhs !check keepdirs"`，且无 `test()`/`check()` 函数、
无 tests 目录、无 CTest/Make check/meson test 入口。搜索证据：
- APKBUILD 全文 grep `^test|^check|checkdepends|checkdepends` 无结果
- options 含 `!check` 显式禁用检查
- 上游无自动化测试可运行，如实记 0；本次测试全部为消费者侧打包完整性验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitLab alpinelinux raw URL 返回 418 | 站点反爬限制 | 使用 git.alpinelinux.org cgit plain URL（aaudit-server 先例同源），字节一致性已核验 |
| 2 | /tmp 只读 | 容器挂载限制 | 工作文件放 ~/alpine-bl-src |
| 3 | protocols/services 不在 aports 内 | 上游 source 指向 Debian netbase v6.4 | 直接从 salsa.debian.org 下载，SHA256 记录在 conandata.yml |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（export_sources + source + build + package + package_info） |
| conandata.yml | 15 个源文件 URL + SHA256 |
| GPL-2.0.txt | 官方 GPLv2 文本（随包安装至 licenses/） |
| manifest.yaml | ARCHIVE-SPEC v2.0 manifest |
| test_package/conanfile.py | 测试入口（self.run 执行 test_smoke.sh） |
| test_package/test_smoke.sh | 9 组真实断言 |
| test_package/MANIFEST.yml | 上游测试声明 |

**最终状态**: built（验证后更新）
---

**编译结束**: 2026-08-12 17:44
**最终状态**: built
