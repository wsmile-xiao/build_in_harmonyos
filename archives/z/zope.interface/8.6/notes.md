# zope.interface 8.6 HarmonyOS 适配笔记

## 范围与分类

lazr.config 依赖链最底层（lazr.config → lazr.delegates → zope.interface）。
setuptools 构建的 Python 包，含**可选** C 扩展
`_zope_interface_coptimizations.c`（setup.py 的 `optional_build_ext` 允许编译
失败回退纯 Python；Jython/PyPy 下 ext_modules=[]）。**纯 Python 回退功能完整**。

## W0 依赖检查

- zope.interface/8.6 配方：**未发布**（本任务新适配包）。证据：`conan download
  zope.interface/8.6 -r=ohpcd --only-recipe` 报 CNB 制品仓 "system acceleration
  policy not enabled"（缺失配方占位响应），直接 API
  `https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/zope.interface/8.6/...`
  HTTP 404，本地 cache 0 命中。
- python/3.12.9 运行时：**已发布**（`conan download python/3.12.9 -r=ohpcd
  --only-recipe` 命中，本地 cache 已含 revision d8eda770878152bea40b42db9f7024cd）。
- PyPI requires_dist 核验：无运行时依赖（仅 docs/test extras：Sphinx、
  zope.event、zope.testing、coverage）。requires_python >=3.10。

## 源码与构建分析

- 官方 sdist：`zope_interface-8.6.tar.gz`，SHA256
  `b40ef9b4873afb5d0dec02b8d2dfde1cf18c72337b60c99cb735961e0bac05c0`
  （与 PyPI JSON digests 一致）。
- 构建元数据：setuptools（pyproject.toml build-backend=setuptools.build_meta）。
- 载荷：`src/zope/interface/`（zope 为 PEP 420 namespace 包，无 __init__.py）。
- 上游测试：`src/zope/interface/tests/`（18 个 unittest 模块）。

## 编译方式决策：纯 Python 打包（不交叉编译 C 扩展）

**技术原因**：
1. 本仓库 CI 对 Python C 扩展交叉编译支持有限（见 build-systems.md §14：
   setup.py build_ext 需交叉 CC/LDSHARED 覆盖、--plat-name、conan 依赖并入
   CFLAGS），风险高收益低。
2. C 扩展是**纯可选加速**：setup.py 的 `optional_build_ext` 在编译失败时
   打印 WARNING 并回退纯 Python——上游设计即允许无 C 扩展部署。
3. 纯 Python 功能完整且被上游支持：zope.interface 上游 CI 有
   `PURE_PYTHON=1`（见 `_compat.py` 文档）纯 Python job。
4. 与 python-dateutil/six 先例一致（python-require 类型、copytree 源码到
   源外 staging）。

因此不评估 C 扩展交叉编译（若将来需要，python/3.12.9 配方提供
include/python3.12 头文件，可参考 lxml/pycairo 配方）。测试在
`PURE_PYTHON=1` 模式下运行（= 本包部署形态）。

## 配方要点（conanfile.py）

- `package_type = "python-require"`；settings os/arch/compiler/build_type。
- 无 requires（无运行时依赖）。
- build()：copytree 源码到**源外** staging `/data/storage/el2/base/cache/zope-interface-stage`
  （同 python-dateutil 教训：不在 build 内递归复制）。
- package()：复制 staging/src/zope → `lib/python3.12/site-packages/zope`，
  ignore tests/、__pycache__、`_zope_interface_coptimizations.c`。
- package_info()：不设 libs（python-require，runtime 由 conanrun 提供）。

## 遇到的工具问题与规避（init-build 嵌套源码误提升）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build "嵌套源码检测: 找到源码在 docs，提升" 后 `.work` 只剩 docs/ 内容 | 工具 `_promote_nested_source` 只认 C 构建标记（configure/CMakeLists/Makefile/meson.build）；zope.interface sdist 根无这些标记，docs/ 有 Sphinx Makefile → 误提升 | 手动 `tar xzf --strip-components=1` 重新解压到 .orig/.work（脚本只读不修改） |

## 依赖版本

- python/3.12.9（已发布 ohpcd）
- 测试期 pip 安装：pytest 9.1.1、zope.testing 6.2（仅上游测试套件所需）

## 验证结果

- 消费者 test_package（test_zi.py）真实调用公开 API：Interface 创建、
  @implementer、classImplements/implementedBy、adapter 注册查询、
  Components 注册 Utility/Adapter、verifyObject/verifyClass——EXIT=0
  （`zope.interface 8.6 OK (C optimizations available: False)`）。
- 上游测试 R51：见 reports/test-report.md（pass_1131_skip_0）。

## 注意事项

- test_package 用 `sys.executable`（conanrun 环境即 python/3.12.9 的 bin）
  执行测试脚本，PYTHONPATH 指向本包 site-packages。
- 若上游后续发布新版本，按 SKILL §1.2 递增版本号。
---

**编译结束**: 2026-09-19 16:45
**最终状态**: built
