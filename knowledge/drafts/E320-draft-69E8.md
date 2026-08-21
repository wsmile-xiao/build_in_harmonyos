# E320 — 纯 Python 包 build() 自检缺运行时 Python 包（本地通过、CI 失败）

## 错误特征

纯 Python 包（无 C 扩展）的 Conan 配方在 `conan-build-test` 阶段失败，日志出现：

```
ModuleNotFoundError: No module named 'unidecode'
  File ".../src/venc3/datastore/__init__.py", line 24, in <module>
    import unidecode
venc-pyc/3.2.7: ERROR: Package ... build failed
```

典型上下文：`build()` 自检 `python3 -c "import ..."` 或 test_package 断言脚本
import 了包内子模块，而该子模块顶层 import 第三方运行时 Python 包。

## 触发条件

- 构建系统: custom（纯 Python / PEP 517）
- 阶段: compilation（build() 自检）/ testing（test_package）
- 关键特征：**本地 conan create 通过，但远程 CI worker 失败**——宿主开发环境
  预装了第三方包，CI worker 为干净环境

## 根因分析

1. 纯 Python 包的 `build()`/`test_package` 自检会 `import` 包内子模块以验证可导入性；
2. 子模块（如 `venc3.datastore`）顶层 `import unidecode` 等第三方运行时 Python 包；
3. 宿主开发环境（pip-global / usr/local）预装了这些包 → 本地验证通过；
4. CI worker 为干净环境（仅 setup.sh 安装的构建工具）→ `ModuleNotFoundError`，
   导致"本地通过、远程 CI 失败"的一次往返（实例：PR #5684 build #27124）。

## 解决方案

### 推荐方案

在 `conanfile.py build()` 与 `test_package/conanfile.py test()` 的
`pip install` 中**显式安装运行时 Python 包依赖**：

```bash
# build() 中（与构建工具一起）
python3 -m pip install flit_core setuptools wheel unidecode pyyaml --quiet
# test_package test() 中
python3 -m pip install unidecode pyyaml --quiet
```

先验证社区源有对应 OHOS 预编译 wheel（避免从 sdist 现场编译）：

```bash
python3 -m pip download unidecode pyyaml --no-deps -d ./dl
# 期望得到 Unidecode-*.whl 与 pyyaml-*-cp312-cp312-ohos_aarch64.whl
```

备选：自检中跳过依赖外部包的子模块（仅 import 无外部依赖的入口模块），
但会削弱验证强度，不推荐。

### 禁止做法

- ❌ 仅依赖宿主环境预装包而 recipe 不显式安装（正是 CI 失败根因）
- ❌ 用 `try/except` 吞掉 ModuleNotFoundError 伪造通过（R40 空壳 stub）

## 验证

```bash
# 清空缓存后全新构建，确认 build() 自检与 test_package 全过
conan remove "venc-pyc*" -c
conan create archives/v/venc-pyc/3.2.7 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 远程：触发 /rebuild 由 CI 干净环境复验
```

## 关联条目

- 相关: E111（Python 包依赖系统 C 库，编译依赖）
- 相关: E319（纯 Python noarch 包 OHOS 适配）
