# 动态文件与目录插件迁移 importlib 时的加载生命周期

以已合入的 Yapsy 1.12.2 为例：从 `imp.load_module` 迁移时，基础插件能加载只证明基础入口可用。还应直接核对目录包的相对导入、模块执行期间的身份，以及 `exec_module` 抛出 `Exception` 后自身缓存键的状态。本条增量是这三个生命周期契约及隔离诊断方法，三步 importlib API 替换本身已有知识覆盖。

## 来源、症状和适用条件

- 原适配：[PR #14350](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14350)，作者 `orrkri`，2026-10-04 06:00:02 +08 合入；固定 head `d7ca3cfeba46bd8c04bf4bd4f471753c99d09c4a`，任务 #12262 已完成。本知识补交不重新认领。
- 上游：[Yapsy 1.12.2 sdist](https://files.pythonhosted.org/packages/source/Y/Yapsy/Yapsy-1.12.2.tar.gz)，83986 字节，SHA256 `d8113d9f9c74eacf65b4663c9c037d278c9cb273b5eee5f0e1803baeedb23f8b`。
- 准确修法：[固定补丁](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/d7ca3cfeba46bd8c04bf4bd4f471753c99d09c4a/archives/y/yapsy/1.12.2/patches/0001-python312-compat.patch)，SHA256 `bc57e738f15b4039affb80d86b21e63db34ec4aff270c742469448a2dbee05dd`。补丁中的版本比较改动不是本条主题。
- 补丁后的 `yapsy/PluginManager.py`：26670 字节，SHA256 `7e8e5c3e528ec746b0cadd7abc2be9f9d44ac56fd99a984c9a4efbd46eccb959`；与原 H1 安装包内源码一致。

触发条件是加载器从单文件或目录入口主动创建并执行模块，目录插件使用 `.helper`，或者插件执行期间读取 `sys.modules[__name__]`。仅迁移 API 后未检查登记时点，可能使相对导入找不到父包，或执行期间取不到自己的模块。执行失败后，若留下未完成的自身模块，也会误导后续同名操作。

本例省略执行前登记的合成反向控制实际产生 `ModuleNotFoundError: No module named '_yapsy_screen_package'`。这是 Windows 诊断夹具的预期失败，不能写成原版 OHOS 失败。不能仅凭任意 `ModuleNotFoundError` 判断加载器有此缺陷；先核真实插件入口、spec、模块名、异常时点和缓存状态。

## 根因和最小修法

[Python 3.12 导入系统的加载规则](https://docs.python.org/3.12/reference/import.html#loading) 说明模块执行前的缓存登记及加载失败清理；[直接导入源文件示例](https://docs.python.org/3.12/library/importlib.html#importing-a-source-file-directly) 也将登记放在执行前。本例遵循相关时点，但不实现完整通用导入协议。

固定补丁中 `_importModule` 的 Python 3 分支为：

```python
is_package = os.path.isdir(candidate_filepath)
module_path = (os.path.join(candidate_filepath, "__init__.py") if is_package
               else candidate_filepath + ".py")
package_paths = [candidate_filepath] if is_package else None
spec = importlib_util.spec_from_file_location(
    plugin_module_name, module_path, submodule_search_locations=package_paths)
if spec is None or spec.loader is None:
    raise ImportError("cannot load plugin module %s from %s" %
                      (plugin_module_name, module_path))
candidate_module = importlib_util.module_from_spec(spec)
sys.modules.pop(plugin_module_name, None)
sys.modules[plugin_module_name] = candidate_module
try:
    spec.loader.exec_module(candidate_module)
except Exception:
    sys.modules.pop(plugin_module_name, None)
    raise
return candidate_module
```

1. 文件输入是去掉 `.py` 的路径；目录输入是包含 `__init__.py` 的目录。本例目录的 `submodule_search_locations` 保留包搜索路径；这不是所有其他加载器都必须显式传同一参数的结论。
2. `module_from_spec` 创建对象后，在 `exec_module` 之前登记它。应在插件顶层直接断言缓存对象的字典就是当前 `globals()`，只在执行结束后比较不足以检查这个时点。
3. 捕获 `Exception` 后移除自身模块键并重抛。应直接检查键已不存在，再用同一未占用名称加载修复文件；错误记录和未注册插件数不能替代这项断言。

此补丁会先移除同名旧对象，因此下述用法要求独立进程内未占用的模块名。本条不提供任意已有模块重载/恢复方案。

## 可复制诊断

只需既有 Python 3 和标准库，无第三方依赖。取得准确受测源码可选择：原 Conan 安装包内的 `lib/python/yapsy/PluginManager.py`，或在自己的临时目录用上列固定 sdist 与补丁还原。后者示例（Git、curl、tar、patch 已可用的类 POSIX 环境；不要求在 Windows 安装它们）：

```sh
git clone --no-checkout https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git framework
git -C framework show d7ca3cfeba46bd8c04bf4bd4f471753c99d09c4a:archives/y/yapsy/1.12.2/patches/0001-python312-compat.patch > yapsy.patch
curl -fL https://files.pythonhosted.org/packages/source/Y/Yapsy/Yapsy-1.12.2.tar.gz -o Yapsy-1.12.2.tar.gz
sha256sum Yapsy-1.12.2.tar.gz yapsy.patch
tar -xzf Yapsy-1.12.2.tar.gz
patch --directory=Yapsy-1.12.2 -p1 < yapsy.patch
sha256sum Yapsy-1.12.2/yapsy/PluginManager.py
```

核摘要与来源表一致后，把下列完整代码保存为 `yapsy_loader_probe.py`；调用 `python yapsy_loader_probe.py /path/to/patched/yapsy/PluginManager.py`。Windows 同样可以向脚本传已保存的源码路径。脚本仅提取准确 AST 函数，不导入整个软件、改写加载算法或修改软件目录；夹具只在临时目录，结束时清理自身键和 helper 键。不要在已运行插件的服务进程内执行此诊断。

```python
import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

source = Path(sys.argv[1])
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "7e8e5c3e528ec746b0cadd7abc2be9f9d44ac56fd99a984c9a4efbd46eccb959")
tree = ast.parse(raw.decode("utf-8"))
cls = next(n for n in tree.body
           if isinstance(n, ast.ClassDef) and n.name == "PluginManager")
fn = next(n for n in cls.body
          if isinstance(n, ast.FunctionDef) and n.name == "_importModule")
fn.decorator_list = []
ns = {"os": os, "sys": sys, "importlib_util": importlib.util}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), ns)
load = ns["_importModule"]
package_name = "_yapsy_screen_package"
failure_name = "_yapsy_screen_failure"
keys = (package_name, package_name + ".helper", failure_name)
assert all(key not in sys.modules for key in keys), "Use a fresh process"
sys.dont_write_bytecode = True
try:
    with tempfile.TemporaryDirectory(prefix="yapsy-loader-probe-") as tmp:
        root = Path(tmp)
        package = root / "package"
        package.mkdir()
        (package / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
        (package / "__init__.py").write_text(
            "from .helper import VALUE\nimport sys\n"
            "SELF = sys.modules[__name__]\n"
            "assert SELF.__dict__ is globals()\nRESULT = VALUE\n",
            encoding="utf-8")
        module = load(package_name, str(package))
        assert module.RESULT == 42
        assert module.SELF is module and sys.modules[package_name] is module
        assert list(module.__path__) == [str(package)]
        print("PASS relative_import_and_during_execution_identity: 42")
        sys.modules.pop(package_name, None)
        sys.modules.pop(package_name + ".helper", None)

        # Same package/spec, deliberately omit preregistration in the control.
        spec = importlib.util.spec_from_file_location(
            package_name, str(package / "__init__.py"),
            submodule_search_locations=[str(package)])
        control = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(control)
        except ModuleNotFoundError as exc:
            assert str(exc) == "No module named '_yapsy_screen_package'"
            print("EXPECTED_FAIL no_preregistration_control: "
                  + type(exc).__name__ + ": " + str(exc))
        else:
            raise AssertionError("Control unexpectedly passed")
        finally:
            sys.modules.pop(package_name, None)
            sys.modules.pop(package_name + ".helper", None)

        failure = root / "failure.py"
        failure.write_text(
            "import sys\nassert sys.modules[__name__].__dict__ is globals()\n"
            "raise ImportError('bounded_probe_failure')\n", encoding="utf-8")
        try:
            load(failure_name, str(failure.with_suffix("")))
        except ImportError as exc:
            assert str(exc) == "bounded_probe_failure"
            assert failure_name not in sys.modules
            print("PASS exception_removes_own_key: absent")
        else:
            raise AssertionError("Failure fixture unexpectedly passed")
        failure.write_text(
            "import sys\nassert sys.modules[__name__].__dict__ is globals()\n"
            "RESULT = 73\n", encoding="utf-8")
        repaired = load(failure_name, str(failure.with_suffix("")))
        assert repaired.RESULT == 73 and sys.modules[failure_name] is repaired
        print("PASS repaired_same_name_reload: 73")
finally:
    for key in keys:
        sys.modules.pop(key, None)
```

输出为三个 PASS 检查和一个 EXPECTED_FAIL 反向控制，整个脚本退出码应为 0；异常信息、预期失败及实际通过分别保留。这个夹具是两项机制比较：目录/身份比较（含反向控制），文件失败/修复比较；不把输出行、API 调用或断言累加成软件消费者数量。

## 实际验证及边界

| 证据层 | 固定结果 | 覆盖和限制 |
|---|---|---|
| 原 H1，OHOS aarch64 / Python 3.12.9 / Conan 2.29.1 | `conan create` RC0，包导入及 100/100（97 上游 + 3 版本兼容） | 基础文件/目录加载和错误上报通过；夹具使用绝对导入，未直接断言本条三项生命周期。原 H1 完整 tar SHA256 `fa8a37cb93c0cb4403dd477f32f87769a6b74ce0ba1bf9e8cd3ab66b53099487`。 |
| 原 A 当前 head 官方 CI | [构建 #69020 / 内部 ID 80233](https://ohpcd.atomgit.com/ci?id=80233) 通过 | 原适配证据；不替代新知识 PR 当前 head 的 CI。 |
| 2026-10-04 Windows / Python 3.11.0rc2，准确加载函数 AST | 目录 helper 值42、执行中身份及 `__path__` PASS；省略登记 EXPECTED_FAIL；ImportError 后主键缺失、修复同名值73及身份 PASS，RC0 | 合成隔离机制比较；不是新增 OHOS 用例、完整 PluginManager 验收或新的 W3。 |

本轮新增软件/H1/W3执行为0，复用固定原件。历史本机完整套件也有失败：Windows Python3.11.0rc2 原基线96/97，multiprocessing权限错误；Windows Python3.14 历史候选上游94/97、完整97/100，有临时目录/进程权限错误；这些不因本条定点比较或 H1 100/100 被改成通过。历史 finish/G0/清理等失败保留于原 A 说明，本条不声称它们全部通过。

明确未覆盖：同名旧对象恢复、此前导入子模块的事务回滚、`BaseException`、Python2回退、spec/loader缺失分支，以及插件实例化/激活异常。Python 标准导入规则涉及 `BaseException`，本补丁实际只捕获 `Exception`；不得把两者写成完全等价。Python3.12目标机未新增本条机制断言。

## 与现有知识的差异及草稿用法

定向排重基线为官方 main `1262b4ac24a3244f254c3e8163fa35d04b48f7fb`（2026-10-04）。最近机制已逐项读全文及相关补丁：

| 近邻 | 已覆盖 | 本条增量 |
|---|---|---|
| [E339](../doc/E339.md) | Waf 的 `imp.new_module`→`types.ModuleType`，保留 exec/cache | 动态目录包搜索上下文、执行期间身份及失败后自身键的直接诊断。 |
| [libfirm 生成器迁移](DRAFT-libfirm-1.22.0-python312-vendored-generators.md) | 三步 importlib API，生成器补丁 | 对应补丁没有目录包分支、预登记或异常清理；三步组合不作为新增点。 |
| [.pth 模块别名](DRAFT-ohos-pythonpath-entry-skips-pth.md) | 已导入模块的别名补录与 .pth 副作用 | 待执行新插件的预登记及执行失败后自身键状态。 |
| [keepkey Python3 迁移](DRAFT-12801-keepkey-agent-0.9.0-py2-protobuf-pb2-py3-migration.md) | 静态相对导入，避免裸名/包名双实例 | 由动态加载器建立包上下文，并在执行期间及失败后直接检查状态。 |

正式知识、草稿和相关 Issue/PR 的定向语义查询没有发现同一组合；草稿目录返回存在截断/缺 blob，PR 初筛是标题查询，不能由此证明全库绝无同题。若后续发现精确同机制内容，应转已有条目补证/更新，不换名重复提交。

配对 KV 的 `doc_file` 以 `knowledge/` 为基准，指 `drafts/DRAFT-yapsy-1.12.2-file-package-loader-lifecycle.md`。当前引擎的 `error_signature` 是 OR 字面片段匹配，关键词另加分；本稿只匹配上文固定反向控制的完整缺父包异常，不将普通 `imp` 缺失、`importlib` 字样或正常加载日志设为错误签名。该预期失败是诊断提示，不能自动判软件失败；主动抛出的 `bounded_probe_failure` 本身也不是缺陷签名，须检查其后的缓存状态。

草稿可人工读取并通过实际解析器/匹配入口校验；未纳入正式索引前不声称全局自动发现。`rec_auto_fix=false`：人工按固定补丁和上文步骤处理，不自动操作模块缓存、不改正式编号或 index。本条仍须新知识 PR 的真实当前 CI、完整 AtomCode 检视和正式审核，原 A 合入/普通积分不等于知识纳入或 B 积分。
