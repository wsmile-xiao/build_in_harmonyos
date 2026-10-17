# DRAFT E430 — `import <name>` 探针被 test_package 同名目录遮蔽（隐式命名空间包）

- **条目主题**：在 `test_package/conanfile.py` 里用 `python -c "import filecheck"` 判断
  「命令行工具是否已安装」，会因为 `test_package/filecheck/` 目录被当作**隐式命名空间包**
  导入成功而恒真 → pip 安装被静默跳过 → 直到 lit 用例报 `command not found (127)`。
- **状态**：草稿（待知识库主编审核提升编号）
- **关联**：riscemu 2.2.7 适配（`archives/r/riscemu/2.2.7/test_package/conanfile.py`）、
  E429（同批：lit 套件环境）、E432（同批：上游测试接入）

## 症状

```text
# conan create 的 test() 里：探针说「已安装」，于是没有 pip install 输出
[test_package] running upstream lit: /.../usr/local/bin/lit --timeout=5 -v .../test_package/filecheck
FAIL: riscemu :: p2align.asm (1 of 11)
# command stderr:
'riscemu': command not found      ← 真正缺的是被测包 bin/ 没进 PATH
error: command failed with exit status: 127
```

另一形态（本次也真实发生）：`filecheck` 可执行文件确实缺失，但探针判定已装：

```bash
$ cd test_package && PYTHONPATH=$PWD:$SP python3 -c "import filecheck"; echo rc=$?
rc=0                      # 假阳性！命中的是 test_package/filecheck/ 目录
$ which filecheck
                          # 实际并不存在（PyPI filecheck 包未安装）
```

## 根因

Python 3.3+ 的 **PEP 420 隐式命名空间包**：任何名为 `filecheck/` 的目录只要出现在
`sys.path` 上，`import filecheck` 就成功（不需要 `__init__.py`）。而 test_package 为了跑
上游 lit 套件，恰好把上游 `test/filecheck/` 复制成了 `test_package/filecheck/`，同时
`test_package` 目录本身又在 `PYTHONPATH` 上（为了让 lit 用例 import 上游 `snitch` 包）。
两者叠加 → `import filecheck` 恒真 → `_ensure_module()` 跳过 `pip install filecheck==0.0.23`
→ 真正缺失的同名 **CLI** 直到 lit 阶段才以 `127` 暴露。

诊断成本被从「装工具阶段」推迟到「跑测试阶段」，且报错信息（`command not found`）
容易误导到被测软件而不是测试工具缺失。

## 修复

工具（CLI）与模块分开探测：

```python
def _ensure_cli(self, env, name, requirement):
    if shutil.which(name, path=env.get("PATH")):
        return
    self._pip_install(env, sys.executable, requirement)
    if not shutil.which(name, path=env.get("PATH")):
        raise ConanException(f"{name} CLI still not found on PATH after installing {requirement}")

# 模块依赖仍可用 import 探针
def _ensure_python_module(self, env, python, module, requirement):
    probe = subprocess.run([python, "-c", f"import {module}"], env=env, capture_output=True)
    if probe.returncode != 0:
        self._pip_install(env, python, requirement)
```

装完必须**复检**并在失败时 `raise`，不允许静默继续。

## 验证

```bash
# 探针应返回非 0（工具未装时）
$ python3 -c "import shutil; print(shutil.which('filecheck'))"   # None
# conan create 日志应出现安装行，且 lit 全绿
$ grep -n "installing test tool: filecheck" reports/conan-create.log
$ grep -n "HMBS_UPSTREAM_SUITE_LIT" reports/conan-create.log     # discovered:11 passed:11
```

## 禁止做法

- ❌ 对命令行工具使用 `import <name>` 探针（存在同名目录时假阳性）。
- ❌ 探针失败后不安装就继续跑测试（错误被推迟并误导归因）。
- ❌ 为了让 `import filecheck` 失败而把 `test_package` 从 `PYTHONPATH` 摘掉 ——
  lit 的 `snitch` 用例（`python3 -m snitch`）随即失败，属于按下葫芦浮起瓢。

## 查重关键词

`import` 探针、隐式命名空间包、namespace package、PEP 420、目录名遮蔽（shadowing）、
`test_package/filecheck`、`shutil.which`、PATH 探针、pip install 被静默跳过、
lit `command not found`、exit status 127
