# mwc 2.0.5 适配笔记

## 上游信息

- 软件：mwc（MailWebsiteChanges）2.0.5 —— 网站变化追踪工具（邮件通知 + RSS feed）
- 上游仓库：https://github.com/mtill/MailWebsiteChanges（Debian 同源码打包）
- 源码包：https://github.com/mtill/MailWebsiteChanges/archive/refs/tags/v2.0.5.tar.gz
- sha256：`c7015cbc84c406995a4e4bcf2302eaf1ef9e9dfb7063a417e4431543d2c67806`（与 Debian 官方 orig tarball 同源，已本地校验）
- 许可证：GPL-2.0-or-later
- 构建系统：无（纯 Python 3 脚本，无 setup.py / pyproject.toml / CMake / autotools）

## 源码审计

- 归档共 7 个文件：`mwc.py`（242 行，主入口）、`mwctools.py`（240 行，解析器库）、`mwcfeedserver.py`（46 行，RSS feed HTTP 服务器）、`config_template.py`（59 行，配置模板）、`README.md`、`LICENSE`、`.gitignore`。
- 入口：`mwc.py --config=<模块名> [--dry-run=<站点名>]`；`mwcfeedserver.py --config= --bind= --port=`。
- 上游无自动化测试：无 tests/ 目录、无 test_*.py、无 pytest/unittest 配置。tarball 中唯一 "test" 字符串是 mwc.py 第 8 行的孤立注释 `#test`。上游真实测试入口 = 工具自身的 `--dry-run` 模式（对 config 模块里声明的站点执行解析链并打印结果）。
- 依赖（README + import 扫描）：Python 3 标准库 + `lxml`（etree）+ `cssselect`（GenericTranslator）。其余全部为标准库。

## 依赖分析（2026-09-21 只读分析，报告 mwc_2.0.5_deps.md）

- `lxml`、`cssselect` 在 ohpcd 均 `conan list Found 0`（未发布）⇒ 不能声明 conan require（R36/L0i 会拦）。
- 两包在 OHOS PyPI 镜像（pypi.cnb.cool/OpenHarmonyPCDeveloper）均可消费：`lxml-6.1.2-cp312-cp312-ohos_aarch64.whl`（预编译 C 扩展 wheel）+ `cssselect-1.5.0-py3-none-any.whl`，pip download EXIT=0。
- 处置：pip vendor 进包内 `deps/`（advocate/1.0.0 先例），`package_info()` 经 runenv 暴露 PYTHONPATH。不声明 conan requires。

## 配方设计

- `package_type = "application"`（CLI 工具，yadm 先例）；settings 全四项但无编译。
- `build()`：① 校验 4 个上游脚本在位 → ② pip install lxml==6.1.2 + cssselect==1.5.0 到 build_folder/deps → ③ 上游 dry-run 冒烟：本地 file:// HTML 站点（2 个 div.ver 条目）+ smokeconfig，跑真实 `mwc.py --dry-run=smoke`，断言输出含 `2.0.5-smoke` 与 `2 results`（走通 URLReceiver→CSSParser→lxml 全链）。
- `package()`：4 脚本 → `bin/`（0755）；`mwctools.py` 额外进 `lib/python3.12/site-packages/`（供消费者 import）；pip vendor 依赖 → `deps/`；LICENSE/README → `share/doc/mwc/`。
- `package_info()`：bindirs=["bin"]，runenv PYTHONPATH 指向 site-packages + deps。
- mwc.py 同目录 import mwctools：运行时 bin/ 下四脚本同目录，`from mwctools import ...` 天然可解析；消费者侧由 site-packages 兜底。

## 上游测试说明

上游 2.0.5 无自动化测试套件（无 tests/、无 test_*.py、无 CI 测试配置）。真实测试入口 = `mwc.py --dry-run=<站点名>`（README "Program execution" 节 + mwc.py:207-231 的 dry-run 分支）。本适配在两层真实执行该入口：

1. **build() 内**：`_run_dryrun_smoke()` 对本地 file:// 站点跑 `mwc.py --dry-run=smoke`，断言 2 条解析结果（离线，不依赖外网）。
2. **test_package 内**：消费者脚本对**安装后的包**（bin/mwc.py + deps/ + site-packages）跑同一条 dry-run 命令，并新增鸿蒙专属消费者用例（见 test_package/MANIFEST.yml）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub/release tarball 与 Debian orig 同源 | 上游 2.0.5 无 GitHub release（mtill/MailWebsiteChanges 最新 tag 停在 2019），Debian 打包者用的 orig tarball 与 GitHub tag 不同源；经 curl+sha256 验证 GitHub tarball 与 Debian orig 完全一致（c7015cbc…78606） | 直接用 GitHub release tarball（PF7/R39 要求 https 官方源，deb.debian.org 被拦"下游重打包"） |
| 2 | lxml/cssselect 无法声明 conan require | ohpcd 两包均未发布（Found 0） | pip vendor 进包内 deps/（advocate 先例），R36/L0i 不受影响 |

## 验证结果

（待 conan create / conan-verify / finish 后回填）
---

**编译结束**: 2026-09-21 03:13
**最终状态**: built
