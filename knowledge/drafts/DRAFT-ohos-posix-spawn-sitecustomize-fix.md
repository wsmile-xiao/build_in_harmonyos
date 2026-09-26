# DRAFT — 上游测试套件内嵌裸名子进程的**零补丁**修法：构建期注入 `sitecustomize` 关闭 `subprocess._USE_POSIX_SPAWN`

> 触发事件：objgraph 3.6.2 HarmonyOS PC 适配（PR #11264，2026-09-19 真机实测）；
> 先例：meson 1.11.0.1（同款修法，见其 notes.md）
> 主从明确：**E405**（OHOS 下 python subprocess 裸名命令不搜 PATH，`_IS_HARMONYOS`
> 强制 `posix_spawn` → Errno 2）为**根条目**；本条补充其**修复手法**面——当裸名调用
> 位于**上游测试源码**内（不能改上游）时，如何零补丁绕过；E405 的 `rec_approach`
> （改写调用方为绝对路径 / `shell=True` / `shutil.which`）对这类场景**不适用**。

## 现象

上游测试套件内以**裸名**启动外部程序，在 OHOS 上即便该程序在 PATH 上且可执行，
仍然报：

```text
FileNotFoundError: [Errno 2] No such file or directory: 'dot'
```

objgraph 实测：不修 → 6 个 doctest 失败，输出为
`Image renderer (dot) not found, not doing anything else`。

## 根因（同 E405）

OHOS 的 CPython 因 `_IS_HARMONYOS` 强制 `subprocess` 走 `posix_spawn` **快速路径**，
而 `posix_spawn`（非 `posix_spawnp`）**不做 PATH 解析**——裸名可执行文件直接抛
`FileNotFoundError`。上游测试源码里 `subprocess.Popen(['dot', ...])` 这类裸名调用
因此失败；Linux/本地开发机上同一代码正常（走 fork/exec → `execvpe` 解析 PATH），
故呈现"本地全绿、OHOS 红"。

## 为什么 E405 的推荐方案在此不适用

E405 的 `rec_approach: use-absolute-path-or-shell-or-which` 要求**改写调用方**——但
裸名调用位于**上游测试源码**（objgraph 的 `tests.py` / doctest 示例、apertium 的
`tests/adaptdocx/__init__.py`）。改写它们等于给上游打补丁：偏离上游、增加维护面、
升级时冲突（R8 补丁规范风险）。**需要一条零补丁的通道**。

## 推荐方案：构建期注入 `sitecustomize.py`，关闭快速路径

在 `conanfile.py` 的 `build()` 里生成一个 `sitecustomize.py`，把
`subprocess._USE_POSIX_SPAWN` 置 False；测试期把该目录前置到 `PYTHONPATH`。
CPython 启动时会自动导入 `sitecustomize`，于是在**不改任何上游文件**的前提下，
`subprocess` 回退到 fork/exec → `execvpe` 正常解析 PATH：

```python
# conanfile.py build() —— 生成 shim
shim_dir = os.path.join(self.build_folder, "sitecustomize")
os.makedirs(shim_dir, exist_ok=True)
save(self, os.path.join(shim_dir, "sitecustomize.py"),
     "import subprocess\n"
     "# OHOS: posix_spawn 不解析 PATH，裸名子进程启动失败\n"
     "subprocess._USE_POSIX_SPAWN = False\n")

# 测试期把 shim 目录放进 PYTHONPATH（优先于 site-packages 解析）
env["PYTHONPATH"] = os.pathsep.join([shim_dir, self.source_folder])
```

**要点**：必须让 `sitecustomize` 处于 `PYTHONPATH` **首位**，且子进程继承该
`PYTHONPATH`（本场景下 pytest 与 dot 均由同一进程树启动，实测生效）。

## 关键坑：`ConanFile.run()` 的 `env=` 不是环境变量字典

想给测试进程传 PATH/LD_LIBRARY_PATH/GVBINDIR 时，很容易写成
`self.run(cmd, cwd=..., env=env_dict)` —— **这会直接抛断言**：

```text
AssertionError: env argument to ConanFile.run() should be a list
  （conan/internal/model/conan_file.py:395）
```

因为 `ConanFile.run()` 的 `env` 参数是**环境文件名列表**（默认
`["conanbuild"]`），**不是**环境变量字典。**正确做法**：临时改写 `os.environ`
（`conan_run()` 以子进程启动命令、继承当前进程环境），并在 `finally` 中还原：

```python
_saved = {k: os.environ.get(k) for k in dot_env}
try:
    os.environ.update({k: v for k, v in dot_env.items() if v is not None})
    self.run(f'"{sys.executable}" tests.py', cwd=self.source_folder)
finally:
    for k, v in _saved.items():
        v is None and os.environ.pop(k, None) or os.environ.__setitem__(k, v)
```

## 要点：外部工具（dot）还需**整条依赖链**的 lib

`dot` 动态链接 graphviz 自身库（libgvc/libcgraph/libcdt…）**以及整条传递依赖链**
（expat/pango/gd/poppler…）。**只把 graphviz 自己的 lib 目录加进 `LD_LIBRARY_PATH`
不够**——实测 `dot -Tpng` 会报 `Format: "png" not recognized`（插件加载失败）。
必须遍历依赖并收集其 `lib` 目录：

```python
for dep in list(self.dependencies.build.values()) + list(self.dependencies.values()):
    if dep.package_folder:
        lib_dirs.append(os.path.join(dep.package_folder, "lib"))
```

另需设置 `GVBINDIR` 指向 graphviz 的插件目录（`<pkg>/lib/graphviz`）。

## 适用面

任何**上游测试源码内含裸名子进程调用**且**不能改上游**的包，在 OHOS 上跑测试时：

- objgraph 3.6.2 → 裸名 `dot`（实测 6 个 doctest 失败 → 修后全通过）
- meson 1.11.0.1 → 同款修法（先例）
- apertium 3.9.12 → 裸名 `python3`/`cat`（该案例采用 **PATH shim（符号链接）** 方案，
  见 `DRAFT-apertium-ohos-python-bare-name-test-subprocess`——两者是同一问题的**
  两条可选通道**：`sitecustomize` 关快速路径 vs PATH 前置 shim）

## 两条通道的选择

| 通道 | 做法 | 适用 |
|---|---|---|
| **sitecustomize（本条）** | 设 `subprocess._USE_POSIX_SPAWN = False`，让 subprocess 回退 fork/exec | 需要在**测试进程内**改变 subprocess 行为；对 Python 内发起的裸名调用通吃 |
| **PATH shim**（apertium 先例） | 建临时 bin 目录，把裸名做成指向绝对路径的符号链接，前置到 PATH | 只需让**某些具体裸名**可被解析；不改运行时语义 |

两者均**零补丁**；选择依据是"要影响 subprocess 全局行为"还是"只补齐几个裸名"。

## 禁止做法

- ❌ 不要为裸名调用给上游测试源码打补丁（偏离上游、升级冲突、R8 风险）。
- ❌ 不要用 `self.run(..., env=<dict>)` 传环境变量（见上文断言坑）。
- ❌ 不要只加 graphviz 自身 lib 就以为 dot 可渲染 PNG（须整条依赖链 + GVBINDIR）。
- ❌ 不要指望 `signal` 处理或改 POSIX 行为开关以外的方式捕获（与 E051 同族教训：
  部分被拦行为的信号不可捕获）。

## 验证证据

- **主证据**：objgraph 3.6.2（PR #11264）真机实测 —— 修前 6 个 doctest 失败
  （`Image renderer (dot) not found`）；修后 `Ran 59 tests in 2.853s` →
  `OK (skipped=2)`，消费者 27/27，`conan create` exit 0。
- **先例佐证**：meson 1.11.0.1 `notes.md:31` ——
  "`sitecustomize.py` 强制 `subprocess._USE_POSIX_SPAWN=False`（走 fork/exec，
  execvpe 解析 PATH）"。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / graphviz 13.1.2 / conan 2.29.1。

## 查重结论

- 对 `sitecustomize` 检索：命中 `DRAFT-ohos-collections-abc-silent-loss`（讲
  `collections.abc` 静默丢失，语境无关）与 meson 的 notes.md（**过程记录，非知识条目**）
  ——**无知识条目覆盖本修法**。
- 对 `_USE_POSIX_SPAWN` 检索：命中 **E405**（根因层，`error_signature` 含
  `_USE_POSIX_SPAWN`）——其 `rec_approach` 是调用方改写，**未含** sitecustomize
  通道；本条为 E405 的**修复手法**差异化补充，E405 保持为根条目。
- 对 `GVBINDIR` / `Format.*png.*not recognized` 检索：无条目覆盖。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
