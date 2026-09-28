# lazr.delegates 2.1.1 适配笔记

## 编译环境
- 构建系统: pysetuptools（纯 Python 包，无 C 扩展、无编译产物）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS aarch64 toolchain，实际无需编译）
- 状态: built
- 依赖: zope.interface/8.6（本链已有适配，conan cache rev b8563506c264593a8652addcc1e214d8）

## 编译步骤

1. 下载官方 sdist：`https://files.pythonhosted.org/packages/6c/55/08f7e5ddb2452f9006186721cdae501906049d847d9611cafca1855d592b/lazr_delegates-2.1.1.tar.gz`
   - sha256 校验：`aeceb2616e51b73f327fbf12c4ec2b7d7670cb820bd5e4f6851215fb796c02dc`（与 PyPI JSON API digest 一致）
2. 解包确认：`__init__.py` 导出 `__all__ = ['Passthrough', 'delegate_to']`；上游测试源齐全（`src/lazr/delegates/tests/{test_api,test_passthrough,test_docs}.py`）
3. 运行上游测试（等价 make check，纯 Python 无 configure/make）：
   ```bash
   cd <sdist 解包> && PYTHONPATH=src python3 -m unittest discover -s src/lazr/delegates/tests -p 'test_*.py'
   # Ran 8 tests — OK（test_api 1 + test_passthrough 4 + docs doctest 3）
   ```
4. conan 配方：python-require 类型，`requires = "zope.interface/8.6"`；build() 将源码 copytree 到源外 staging（`/data/storage/el2/base/cache/lazr-delegates-stage-2.1.1`），package() 复制 `src/lazr/`（含 lazr/delegates）与 `src/lazr.delegates.egg-info` 到 `lib/python3.12/site-packages`。
5. `conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`：配方自包含构建 + test_package 真实调用 API（delegate_to + Passthrough）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 的 find_project_dir() 从脚本目录向上找 SKILL.md，命中技能根目录而非工作仓库 | 环境存在两个 SKILL.md（技能根 + 工作仓库），向上遍历优先命中前者 | 所有 ohc-run.py 调用前 `export OHC_PROJECT_DIR=<工作仓库根>`（find_project_dir 优先级 1） |
| 2 | conan-init 自动模板为 Autotools（configure+make），对纯 Python 包完全不适用 | 模板按 build_system 猜测，init-build 报 "custom 模板不可用" | 手动替换为 python-require 配方（参照 zope.interface/8.6 与 lazr.delegates/4.0.0 先例） |
| 3 | conandata.yml 自动生成 sha256 为 REPLACE_WITH_ACTUAL_SHA256 | 模板占位符 | 填入官方 sha256（PyPI JSON API 核验） |
| 4 | test_package 自动生成 C/CMake 测试壳（test.c + CMakeLists.txt） | 通用模板 | 删除，改写为 python-require 测试：test() 收集被测包与依赖的 site-packages，`self.run(python3 test_lazr_delegates.py <site-packages>)` |
| 5 | 上游 test_docs.py 直接 `import pkg_resources`（非 try/except） | 上游代码 | 环境 python 已装 setuptools（pkg_resources 可用）——无需 patch；运行时包不依赖 pkg_resources（namespace `__init__.py` 有 try/except 兜底） |
| 6 | 平台 write/edit 工具 scope 指向沙箱 archives 根，而 ohc-run 工具与 git 仓库在另一个项目根 | 平台 sandbox 映射与工具链项目根不一致 | 配方文件先在沙箱写入，再同步到仓库路径（仓库为工具链与 git 唯一权威） |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| zope.interface | 8.6 | 运行时唯一依赖（classImplements）；本地 conan cache rev b8563506c264593a8652addcc1e214d8 |
| python | 3.12.9 | 环境解释器（site-packages 目标 lib/python3.12） |

## 验证结果

```bash
# 上游测试（8/8）
PYTHONPATH=src python3 -m unittest discover -s src/lazr/delegates/tests -p 'test_*.py' -v
Ran 8 tests ... OK

# conan 配方 + test_package
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package: lazr.delegates 2.1.1 OK (version=2.1.1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | python-require 配方（source()/build()/package()/package_info()） |
| conandata.yml | 官方 URL + sha256（无补丁） |
| test_package/ | conanfile.py + test_lazr_delegates.py + MANIFEST.yml（真实调用 API） |
| manifest.yaml / notes.md | 版本级元数据 + 本笔记 |
| reports/test-report.md | 上游测试 8/8 记录 |

## 注意事项

- 2.1.1 与 4.0.0 的差异：2.1.1 的 `src/lazr/__init__.py` 存在（namespace 包，pkg_resources try/except），4.0.0 无；两者 import 均调用 `importlib.metadata.version("lazr.delegates")`，必须携带 egg-info。
- 上游测试用 `pkg_resources`（test_docs.py），仅测试环境需要 setuptools，运行时包不依赖。
- 本包无补丁、无平台宏、无编译——纯打包适配。
---

**编译结束**: 2026-09-21 21:15
**最终状态**: built
