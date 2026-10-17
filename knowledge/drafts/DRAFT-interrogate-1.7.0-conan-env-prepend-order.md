# draft-interrogate-1.7.0-conan-env-prepend-order

## 症状

两个场景、同一个根因家族：

**场景 A（构建期，套件收集即死）**：

```
ImportError: cannot import name 'io' from 'py' (.../build-release/test-deps/py.py)
ERROR tests/functional/test_coverage.py
ERROR tests/functional/test_cli.py
Interrupted: 3 errors during collection!
```

vendored 的 `py/` 包明明铺在 staged 树里，`import py` 却解析到了 test-deps 目录下的 `py.py`（pytest 9.x 自带的模块级 shim 文件，无 `io` 子模块）。

**场景 B（消费者，test_package 来源校验失败）**：

```
AssertionError: colorama was imported from outside its package folder:
/data/storage/el2/base/files/interpreters/pip-global/colorama/__init__.py
(expected under /storage/Users/currentUser/.conan2/p/colorfe6f6c8f8dff9/p)
```

conan 的 colorama 包在磁盘上、PYTHONPATH 里也有它的路径，import 却落到了宿主解释器的 pip-global 树。

## 根因

1. **`Environment.prepend_path` 是栈式组合**：对同一变量多次 prepend，**后调用的值排在最前面**。"先写最主要的路径"这种直觉写法恰好把次要路径推到前面——先 prepend staged 树、再 prepend test-deps，结果是 test-deps 在前，pytest 的 py.py shim 遮蔽 vendored py/ 包。
2. **`append_path` 把宿主环境留在前面**：package_info 里对依赖路径用 append，宿主 PYTHONPATH（本机 pip-global、CI worker 各不相同）继续抢占解析次序，打包依赖被遮蔽。

叠加态：pytest ≥9 自带模块级 py.py shim，任何把它所在目录排在名为 `py` 的真实包之前的 PYTHONPATH 都会让 `from py import io` 落到 shim 上。

## 解决

- 构建期套件环境：**反序 prepend**——依赖路径先 prepend、test-deps 其次、staged 树最后（占最前位）。
- package_info 导出：**全部 prepend_path，禁用 append_path**；依赖先 prepend、包自身 site 最后（最前），形成 `<包site>:<依赖...>:<宿主环境>`。
- 来源校验（test_package 里逐依赖 import 并断言 `__file__` 前缀在各自包文件夹内）是发现遮蔽的探针；没有它，遮蔽表现为"本机绿、CI 红"或"负向测试假通过"。

## 验证

```
# 复现 A：先 prepend site 再 prepend test_deps → 3 errors during collection (ImportError: py)
# 修复 A：反序 → 228 passed / 13 skipped
# 复现 B：package_info 用 append_path → provenance 断言失败（pip-global 抢答）
# 修复 B：全改 prepend_path → INTERROGATE_CONSUMER=PASS assertions=33
```

## 迁移建议

- 写多路径 PYTHONPATH 组合时，从最后一个 prepend 往回推想要的最终次序。
- 消费者测试必须带 provenance 断言（import 路径前缀校验），把环境遮蔽变成硬失败。
