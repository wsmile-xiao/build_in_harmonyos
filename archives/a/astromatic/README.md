# astromatic (AstrOmatic 套件元包)

## 是什么

astromatic 是 Debian 原生元包（metapackage）：自身不含任何源码/构建产物，
仅聚合 AstrOmatic 套件工具。上游 VCS salsa.debian.org/debian-astro-team/astromatic，
本仓移植为 **requirements-only 聚合 Conan 配方**（仓内首个此类配方）。

## 聚合内容（上游 debian/control Recommends，7 项）

| 工具 | 版本 | 二进制 | 状态 |
|------|------|--------|------|
| missfits | 2.8.0 | missfits | ohpcd 已发布 |
| psfex | 3.24.2 | psfex | ohpcd 已发布 |
| scamp | 2.15.0 | scamp | ohpcd 已发布 |
| source-extractor | 2.28.2 | sex, ldactoasc | 本仓同批适配 |
| stiff | 2.4.0 | stiff | ohpcd 已发布 |
| swarp | 2.41.5 | swarp | ohpcd 已发布 |
| weightwatcher | 1.12 | ww | ohpcd 已发布 |

## OHOS 适配

- 无编译、无补丁；风险集中在依赖闭包（source-extractor，见其 2.28.2/notes.md）。
- package_type=unknown（Conan 2.29 无 meta-package 枚举），settings 含
  os/compiler/build_type/arch（L0p 门禁）。
- CI L1 无上游测试 → ci/config/no_official_test.txt 白名单（skip=whitelisted）。
- test_package 冒烟 7 个依赖二进制（--version / -v / --help）。

## 参考资料

- 上游：https://salsa.debian.org/debian-astro-team/astromatic
- 官网：https://www.astromatic.net/software/
