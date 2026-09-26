# E634 — setuptools_scm 包从发布 tarball 构建取不到版本，需注入 SETUPTOOLS_SCM_PRETEND_VERSION

- **状态**: 草稿（contributor U4D2）
- **严重度**: 2（medium）
- **阶段**: installation
- **来源事件**: undertime 4.3.1 适配（2026-09-24）

## 错误特征

```
  Preparing metadata (pyproject.toml): finished with status 'error'
  error: subprocess-exited-with-error
          raise LookupError(error_msg)
      LookupError: setuptools-scm was unable to detect version for /path/to/src.
      Alternatively, set the version in the environment with
      SETUPTOOLS_SCM_PRETEND_VERSION_FOR_<DIST> or VCS_VERSIONING_PRETEND_VERSION_FOR_<DIST> ...
error: metadata-generation-failed
× Encountered error while generating package metadata.
```

注意失败发生在 **metadata 生成阶段**，还没到编译/安装；日志里往往只有 `metadata-generation-failed`，
真正的 `LookupError` 埋在子进程回溯里。

## 触发条件

1. 上游用 setuptools_scm 作为版本来源：

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=42", "wheel", "setuptools_scm[toml]>=3.4"]
build-backend = "setuptools.build_meta"

[tool.setuptools_scm]
```

```python
# setup.py
setup(use_scm_version=True)
```

2. 配方的 `source()` 取的是**上游发布 tarball**（`git archive` 产物）——里面没有 `.git`，也没有
   `.git_archival.txt`，setuptools_scm 无从推导 tag。

## 根因

setuptools_scm 的版本来自 VCS 元数据（git tag / 归档元数据）。发布 tarball 二者皆无，于是抛
`LookupError`。这与"配方写错了"无关：同一份源码用 `git clone` 检出就能构建成功，用 tarball 就失败——
很容易误判成源码包损坏。

## 解决方案（推荐）

构建时给子进程注入配方声明的版本：

```bash
SETUPTOOLS_SCM_PRETEND_VERSION=4.3.1 python3 -m pip install \
    --no-deps --no-build-isolation --prefix=<私有 prefix> <源码目录>
```

配方里的写法（undertime 4.3.1）：

```python
self._pip(
    ["--no-deps", "--no-build-isolation", "--prefix=" + prefix, self.source_folder],
    extra_env={
        "PYTHONPATH": deps_build,
        "SETUPTOOLS_SCM_PRETEND_VERSION": str(self.version),
    },
)
```

版本值取自配方自身的 `self.version`，天然与 `conandata.yml`/归档目录一致，不会漂移。

## 验证证据（可复现）

```bash
# 不注入（复现失败）
$ env -u PIP_TARGET PYTHONPATH=<setuptools+wheel+setuptools_scm 目标> \
  python3 -m pip install --no-deps --no-build-isolation --prefix=$HOME/tmp/pfxA <源码目录>
  Preparing metadata (pyproject.toml): finished with status 'error'
  LookupError: setuptools-scm was unable to detect version for .../srcA.        # ← 实测

# 注入后（成功）
$ env -u PIP_TARGET PYTHONPATH=<同一后端> SETUPTOOLS_SCM_PRETEND_VERSION=4.3.1 \
  python3 -m pip install --no-deps --no-build-isolation --prefix=$HOME/tmp/pfxC <源码目录>
Successfully built undertime
Successfully installed undertime-4.3.1                                          # ← 实测
```

端到端佐证：undertime 4.3.1 的 `conan create` 通过，包内 `bin/undertime --version` 输出 `4.3.1`
（该值经 importlib.metadata 从 dist-info 读出，说明注入的版本确实落进了元数据）。

## 适用边界

- 适用：任何 setuptools_scm（或同类 VCS 版本插件）驱动版本、且由 tarball 构建的 Python 包。
- 不适用：版本写在 `setup.cfg`/`pyproject.toml` 字面量里的包；源码以完整 git checkout 提供的包；
  tarball 带 `.git_archival.txt` 且上游启用了 archival 支持的包。

## 不适用 / 禁止

- ❌ 手改上游 `setup.py`/`pyproject.toml` 把版本写死：改动上游源码绕过构建期问题，升级易漏改。
- ❌ 事后手工拼接/伪造 dist-info 元数据：`importlib.metadata` 读到的版本不可信，消费者 `--version` 与包内容不符。

## 关联条目

- 无直接同族条目（查重覆盖 `knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/`，未命中
  `setuptools_scm` / `PRETEND_VERSION` / `use_scm_version`）。与 E633 同属"配方内 pip 调用需要控制子进程
  环境"，但触发面（VCS 版本探测 vs 机器级 pip 配置）与修复手段不同，故独立成条。
