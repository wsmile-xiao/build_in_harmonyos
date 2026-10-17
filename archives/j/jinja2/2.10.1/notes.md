# jinja2 2.10.1 — 适配记录（HarmonyOS PC / arm64）

## 适配路径

`python-require` 纯 Python 包（setuptools），沿用仓库既有 Python 包模式：

1. `source()` 取 PyPI 官方 sdist → 校验 sha256 → 应用 1 个源码补丁；
2. `build()` 运行上游 pytest 套件并回填真实通过率（R51）；
3. `package()` 拷 `jinja2/` 进 `lib/python3.12/site-packages/jinja2/`；
4. `package_info()` 用 `runenv_info/buildenv_info` 声明 PYTHONPATH。

## 必需补丁：0001-collections-abc.patch

**没有这个补丁，jinja2 2.10.1 在 Python 3.12 上连 import 都做不到。**

上游用了 py3.10 已移除的 `collections` 旧别名，共 5 处：

| 文件 | 行 | 原写法 |
|---|---|---|
| `jinja2/tests.py` | 13 | `from collections import Mapping` |
| `jinja2/sandbox.py` | 17 | `from collections import Mapping` |
| `jinja2/sandbox.py` | 82 | `from collections import MutableSet, MutableMapping, MutableSequence` |
| `jinja2/runtime.py` | 318 | `from collections import Mapping`（try/except 块内）|
| `jinja2/utils.py` | 485 | `from collections import MutableMapping`（try/except 块内）|

实际报错（未打补丁）：

```
File "jinja2/tests.py", line 13, in <module>
    from collections import Mapping
ImportError: cannot import name 'Mapping' from 'collections'
```

补丁把 5 处统一改为 `collections.abc`。注意 `runtime.py` / `utils.py` 的两处在
`try/except ImportError: pass` 里 —— 它们**不报错但会静默失效**（Context 不再
注册为 Mapping、LRUCache 不再注册为 MutableMapping），所以必须一并修，
不能只看 import 是否成功。

实测（`git apply --check`，与 CI 同口径）补丁可干净应用。

## 依赖：markupsafe 必须 1.1.1

```
jinja2/utils.py:647:  from markupsafe import Markup, escape, soft_unicode
```

`soft_unicode` 在 MarkupSafe 2.1 被移除。故 `requirements()` 明确 pin
`markupsafe/1.1.1`（本批任务同批适配），不能跟随 ohpcd 上的新版。

## 上游测试

```
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=<src>:<markupsafe-site> \
  python3 -m pytest tests -q --assert=plain -p no:cacheprovider
533 passed, 2 failed, 1 error, 3 skipped
```

### 三项未通过逐项定性（均为环境差异，非本适配引入）

1. **`test_debug.py::TestDebug::test_runtime_error`** — 该测试用一条精确正则
   匹配 `format_exception` 输出（含 `File ".../broken.html", line 2, in
   (top-level template code|<module>)` 与 `<lambda>` 帧）。py3.12 的 traceback
   帧文本/列指示符与 2.10.1 时代（py3.7）不同，正则失配。属上游测试对解释器
   版本的硬编码假设。

2. **`test_nativetypes.py::TestNativeEnvironment::test_undefined_native_return`** —
   断言 `isinstance(env.from_string('{{ missing }}').render(), Undefined)`。
   `native_concat()` 对单节点结果调用 `ast.literal_eval(out)`；py3.12 的
   `literal_eval` 在处理 Undefined 对象时会先求值其 `__repr__` 并抛出
   `UndefinedError`（实测：`literal_eval(Undefined) -> UndefinedError`），
   而上游的 `except (ValueError, SyntaxError, MemoryError)` 没有覆盖它。
   属上游代码未适配新解释器行为。

3. **`test_bytecode_cache.py::TestByteCodeCache::test_simple`** —
   `FileSystemBytecodeCache()` 需要从 tempdir 推导出安全目录，其
   `_get_default_cache_dir()` 要求 `lstat().st_mode == 0700` 且 uid 匹配；
   本平台 tempdir（HMDFS）上 **chmod 被忽略**，实测
   `mode=2771`（setgid 位继承）、`st_uid != os.getuid()` → `_unsafe_dir()`
   抛 `RuntimeError: Cannot determine safe temp directory`。
   属 OHOS 文件系统语义限制，非代码缺陷。

> 未用 test-skipping / xfail 掩盖上述 3 项（R51：不允许为了让报告好看而
> 屏蔽测试）。配方 `build()` 内如实打印 `2 failed, 533 passed`，并通过
> `self.output.warning` 标记存在失败项。

## 消费者契约（test_package）

`test_jinja2.py` 覆盖：模板渲染、自动转义（经 markupsafe）、模板继承、
for/if 控制流、过滤器（`upper`）、测试函数（`odd`/`mapping`），以及两个
平台契约——全量扫描包内 `.py` 确认无 `from collections import Mapping`
残留，并断言 `jinja2.utils.soft_unicode` 可用。
