# E633 — 环境级 PIP_* 配置让配方内的私有 --prefix 安装失败

- **状态**: 草稿（contributor U4D2）
- **严重度**: 2（medium）
- **阶段**: installation
- **来源事件**: undertime 4.3.1 适配（2026-09-24）

## 错误特征

```
ERROR: Cannot set --home and --prefix together
```

（部分 pip 版本措辞为 `Can not combine '--target' and '--prefix'`。）

## 触发条件

1. 机器级 pip 配置来自环境变量而不是配置文件：

```bash
$ pip3 config list
:env:.index-url='https://.../simple'
:env:.no-input='1'
:env:.only-binary=':all:'
:env:.target='/data/storage/el2/base/files/interpreters/pip-global'
:env:.trusted-host='...'
```

2. 配方在 `build()` 内调 pip，并显式指定私有安装目标（`--prefix=<build_folder>/prefix` 或
   `--target=<build_folder>/deps`）——这是 R49 要求的标准做法。
3. 子进程继承了上面那些 `PIP_*` → 环境里的 `PIP_TARGET` 与命令行的 `--prefix` 冲突。

## 根因

pip 的环境变量配置（`PIP_*`）优先级**高于**命令行参数。环境里已经设了 `PIP_TARGET`（等价于
`--target`/`--home` 语义），再叠加命令行 `--prefix`，pip 在参数校验阶段就直接报错退出——根本没走到
安装逻辑。所以这不是"路径写错"，而是"安装目标被机器级配置劫持"。

危害不止报错一种：即使不冲突，`PIP_TARGET` 会把依赖装进共享目录、`PIP_ONLY_BINARY=:all:` 会改变解析
策略、`PIP_INDEX_URL` 会顶掉显式传入的镜像地址——三者都会让配方行为随机器而变（本地能过、CI 挂）。

## 解决方案（推荐）

在配方内调用 pip 前剥离全部 `PIP_*`，再显式传参数：

```python
env = {k: v for k, v in os.environ.items() if not k.startswith("PIP_")}
env["PIP_NO_INPUT"] = "1"
cmd = [sys.executable, "-m", "pip", "install",
       "--index-url", MIRROR, "--trusted-host", HOST,
       "--no-input", "--no-compile", "--target=" + deps]
subprocess.run(cmd, check=True, env=env)
```

## 验证证据（可复现）

```bash
# 复现：保留环境里的 PIP_TARGET，命令行走私有 --prefix
$ PIP_TARGET=$HOME/tmp/pipglobal PYTHONPATH=<setuptools 后端> SETUPTOOLS_SCM_PRETEND_VERSION=4.3.1 \
  python3 -m pip install --no-deps --no-build-isolation --prefix=$HOME/tmp/pfx .
ERROR: Cannot set --home and --prefix together          # ← 实测

# 隔离确认只有 PIP_TARGET 触发（PIP_ONLY_BINARY 单独设置不触发）
$ env -u PIP_TARGET -u PIP_INDEX_URL -u PIP_TRUSTED_HOST PIP_ONLY_BINARY=:all: \
  python3 -m pip install ... --prefix=$HOME/tmp/pfx .
（无报错）

# 修复：剥离全部 PIP_* 后同一命令
$ env -u PIP_TARGET -u PIP_ONLY_BINARY -u PIP_INDEX_URL -u PIP_TRUSTED_HOST \
  PYTHONPATH=<setuptools 后端> SETUPTOOLS_SCM_PRETEND_VERSION=4.3.1 \
  python3 -m pip install --no-deps --no-build-isolation --prefix=$HOME/tmp/pfx .
Successfully built undertime
Successfully installed undertime-4.3.1                   # ← 实测，且 prefix/bin 下出现 undertime/moonphases
```

undertime 4.3.1 实测：`conanfile.py` 内三处 pip 调用（构建后端、运行时依赖、本体安装）全部走剥离后的
环境，`conan create` 通过，包内 `bin/` 与 `lib/python3.12/site-packages/` 产物齐全。

## 适用边界

- 适用：任何在 `build()`/`test()` 内调 pip 且指定私有安装目标的配方；纯 Python 包、pybind11 绑定包、
  用 pip 装工具的包都算。凡是"本地能过、CI 挂"或"换台机器就挂"的 pip 安装问题，先查这一条。
- 不适用：不调 pip 的配方；或用 `--target` 之外完全不涉及安装目标的场景。

## 不适用 / 禁止

- ❌ 不剥离 `PIP_*` 却依赖 `--prefix`/`--target`：安装目标随机器而变，可能写入共享目录。
- ❌ 把 pip 依赖装进 `/usr/local` 等共享 prefix：违反 R49，跨任务污染且不可回滚。

## 关联条目

- 无直接同族条目（查重覆盖 `knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/`，未命中
  `PIP_TARGET` / `--prefix` / `pip config` 相关记录）。与 E049（脚本内硬编码路径导致不可移植）在
  "配方行为不应依赖机器级环境"这一点上思路相近，但触发面与修复对象不同。
