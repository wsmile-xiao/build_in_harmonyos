# lazy-object-proxy 1.12.0 — OHOS（鸿蒙 PC）适配笔记

## 概述

lazy_object_proxy 是 Python 的惰性对象代理库（目标对象仅在首次访问时创建），
带 C 扩展加速实现 `cext`（`src/lazy_object_proxy/cext.c`，只用 CPython API、
无外部 C 库依赖）+ 纯 Python 回退实现（simple/slots）。属**必须编译**的
Python 包（与仓内 psutil / cffi / lxml 同类），`os=OHOS, arch=armv8`，
路径 A 基础适配。

上游版本对应：1.12.0（github.com/ionelmc/python-lazy-object-proxy，
PyPI sdist sha256=1f5a462d92fd0cfb82f1fab28b51bfb209fabbe6aabf7f0d51472c0c124c0c61）。

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | setuptools（pyproject build-backend=setuptools.build_meta，要求 setuptools>=80、setuptools_scm>=8） |
| 编译日期 | 2026-10-05 |
| 目标 | aarch64-linux-ohos（os=OHOS, arch=armv8） |
| 工具链 | clang 15（OHOS profile），-fuse-ld=bfd |
| 状态 | built（本地 conan create） |

## 编译步骤

```bash
conan create archives/l/lazy-object-proxy/1.12.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

1. `source()` 下载 PyPI sdist（sha256 校验）并解压
2. `build()` 引导 setuptools（pip 镜像）→ `setup.py build_ext --inplace`
   编 `cext.cpython-312-aarch64-linux-ohos.so` → 签名 → 跑上游 pytest 套件
3. `package()` 拷 `src/lazy_object_proxy` → 再签一次 → 声明 PYTHONPATH
4. test_package 消费者测试（import/惰性语义/cext 后端/OHOS 平台校验）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决 |
|---|---|---|---|
| 1 | 上游 pytest 收集阶段 `'benchmark' not found in markers` 中断（4 errors during collection） | tests/test_lazy_object_proxy.py 的 test_perf/test_proto 用 `benchmark` fixture + `@pytest.mark.benchmark`（上游 tox 环境装 pytest-benchmark）；且配方设 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 后插件不会自动加载 | 测试依赖加 pytest-benchmark（pip 镜像引导）+ pytest 命令显式 `-p benchmark` |
| 2 | `ModuleNotFoundError: No module named 'lazy_object_proxy'` | 上游 src 布局（package_dir={"": "src"}），PYTHONPATH 指到了 source 根而非 `src/` | PYTHONPATH 前置 `<source>/src` |
| 3 | test_package 阶段 `Proxy.__module__ == 'builtins'` 误判为"纯 Python 回退被选用" | cext.Proxy 是 C 实现类型，`__module__` 为 `'builtins'`（C 类型无源码模块）——**这正是 C 扩展被选用的特征**；纯 Python 回退才报 `lazy_object_proxy.simple` | 断言改为 `lop.Proxy is not cext.Proxy`（对象同一性判定） |
| 4 | test_package 阶段 `sys.platform == 'linux'`（应为 ohos） | conan python 依赖经 conanrun 注入的 LD_LIBRARY_PATH 命中 conan 版 libpython3.12.so，宿主解释器身份被翻转（sys.platform 由 ohos 变 linux；cffi 2.1.1 先例 DRAFT-ohos-conan-libpython-hijacks-host-interpreter 同一结论） | test_package 手动构造环境：PYTHONPATH 前置产物 site + 从 LD_LIBRARY_PATH 剔除 conan python 的 lib，用系统 OHOS 原生 python3（CPython 3.12.9，EXT_SUFFIX .cpython-312-aarch64-linux-ohos.so 与产物 ABI 一致） |

## 测试结果（conan create 实跑，2026-10-06）

**上游 pytest 套件**（tests/ 参数化 slots/cext/simple × subclassed/normal，
含 src doctest，9.59s）：

```
1601 passed, 4 skipped, 44 xfailed, 46 xpassed
```

- 通过率：1601/(1601+0) = **100%**（分母不含上游自身 skip/xfail）
- 零失败：exit=0，无清单外失败
- cext 参数（本适配核心交付物）全参数化用例通过

**test_package 消费者测试**（import/惰性语义/cext 后端/OHOS 平台校验）：

```
PASS: lazy-object-proxy consumer checks all green
```

- Proxy backend module: builtins（cext C 类型特征，确认 C 扩展被选用）
- sys.platform: ohos（OHOS 原生环境校验通过）
- cext.cpython-312-aarch64-linux-ohos.so（aarch64-linux-ohos ABI + ELF 校验通过）
