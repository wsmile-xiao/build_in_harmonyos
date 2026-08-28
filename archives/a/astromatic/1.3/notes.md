# astromatic 1.3 适配笔记（OHOS PC, aarch64）— requirements-only 聚合元包

## 上游事实（联网核验）

- astromatic 是 Debian 原生元包：无源码/构建/测试，仅聚合 AstrOmatic 套件。
- 上游 VCS salsa.debian.org/debian-astro-team/astromatic，tag debian/1.3
  （commit 84efd9c66097e42f7f4e957a8c90c96a029ba437，release 2022-12-26）。
- debian/control（salsa raw + sources.debian.org 双源核验一致）Recommends 7 项：
  missfits, psfex, scamp, source-extractor, stiff, swarp, weightwatcher。
- changelog：1.2 起 sextractor 更名 source-extractor；1.3 = multi-arch foreign。
- Homepage https://www.astromatic.net/software/。

## 本仓移植形态

- conanfile.py 为 requirements-only 聚合（首个先例）：name=astromatic /
  version=1.3，package_type=unknown（Conan 2.29 无 meta-package 枚举），
  settings 含 os/compiler/build_type/arch（L0p 门禁要求）。
- requires 对齐上游 Recommends 7 项；其中 6 项已在 ohpcd 发布，
  source-extractor 2.28.2 由本轮同批新建配方（archives/s/source-extractor）适配。
- 无 build/source/package 方法；conandata.yml 记录 Salsa 官方源 URL/SHA256
  （配方不下载，供 CI source_trace 审计）。
- 无 commands.json（元包无二进制；L0k 判定为库型不要求）。
- CI L1：无上游测试 → 加入 ci/config/no_official_test.txt 白名单（skip）。

## 测试语义

- 上游无任何测试（元包，无 autopkgtest/make check）。
- test_package 冒烟 7 个依赖工具二进制真实执行（--version / -v / --help，
  各工具 flag 按其独立配方的消费者测试实测确定），VirtualRunEnv 提供
  PATH/LD_LIBRARY_PATH。
- 统计口径：test_package 冒烟断言数（assertion_count=7）。

## OHOS 要点

- metapackage 无编译，无 OHOS 补丁；风险主要在依赖闭包（source-extractor）。
- 命名一致性：conanfile.name=astromatic 与目录 archives/a/astromatic 一致
  （L0m-4）。

## 参考

- 同生态 6 工具配方（scamp/stiff/swarp/missfits/psfex/weightwatcher）均已合入。
- skymaker 3.10.5 不在上游 Recommends 内（未纳入本元包）。
