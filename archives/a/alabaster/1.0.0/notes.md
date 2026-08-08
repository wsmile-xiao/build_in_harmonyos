# Adaptation Notes - alabaster 1.0.0

## Overview
alabaster 是 Sphinx 的默认文档主题（light, configurable Sphinx theme），
提供 HTML 模板（layout/about/navigation/relations/donate）、theme.conf 配置、
以及 Pygments 高亮样式（alabaster.support.Alabaster）。

## Build System
- flit_core（`pyproject.toml` build-backend = flit_core.buildapi）
- 纯 Python wheel（py3-none-any）— 无 C/C++ 编译
- Runtime deps: `dependencies = []`（pyproject 声明为空）

## Build Process
1. 下载 PyPI sdist `alabaster-1.0.0.tar.gz`
2. `pip install flit_core pygments`（构建后端 + support.py 运行依赖）
3. `pip install --no-deps --prefix=$staging .` 然后归一化到 `lib/pythonX.Y/site-packages`
4. 复制 LICENSE.rst 到 licenses/
5. test_package: import + 版本 + 主题文件完整性 + theme.conf 解析 + setup() 钩子（FakeApp）+ update_context + Pygments 样式

## Upstream Tests
- 上游 sdist **无测试文件**（无 test/ 目录，纯 Python 主题包）。
- test_package 补全 7 个消费者测试（test_package/test_alabaster.py），全部不依赖真实
  Sphinx 文档构建，可在 OHOS 受限环境运行：
  1. test_import_and_version — import + __version__ == "1.0.0"
  2. test_get_path — 主题目录存在且含 theme.conf
  3. test_theme_templates_present — HTML 模板文件完整性
  4. test_theme_conf — theme.conf [theme]/[options] 解析（configparser）
  5. test_setup_hook — Sphinx setup() 注册流程（FakeApp 模拟，require_sphinx/add_html_theme/connect）
  6. test_update_context — html-page-context 注入 alabaster_version/show_sphinx
  7. test_pygments_style — support.Alabaster 样式类

## OHOS-specific handling
- 纯 Python noarch：settings 仅 ("os", "arch")，无需编译器（R32 平台判断用 in ("Linux", "OHOS")）。
- HMDFS umask 077 权限问题：本包无 .so 产物，pip --prefix 安装到 staging 不涉及
  ~/.local 权限问题（对比 acronym 需修复 site-packages 权限）。
- build() 中 pip 安装 flit_core/pygments 使用 --break-system-packages + 超时重试，
  规避 CI 干净环境无预装问题。

## 验证
- conan create: PASS（7/7 test_package 通过）
- 版本号：1.0.0（上游首次适配，R37）

## 已知限制
- 完整 Sphinx 文档构建（sphinx-build）不在本包测试范围——alabaster 是主题包，
  L1 验证覆盖 import/API/模板完整性；真实渲染依赖 Sphinx 本体（非本包依赖）。
---

**编译结束**: 2026-08-08 01:53
**最终状态**: built
