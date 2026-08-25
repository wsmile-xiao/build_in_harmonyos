# DRAFT-pico-sdk-shadow-ci-isolated-home-pythonpath：shadow HOME 隔离时复用已安装 Conan 依赖

> Contributor: pico-sdk 2.2.0 适配 | Status: Draft | Updated: 2026-08-25
> Source: shadow CI r1 setup fail / r2+ env probe pass

## 现象

pico-sdk shadow CI r1 在 setup 阶段失败。脚本进入 “Conan not found or broken, installing” 分支，随后公网 pip 下载超时；重试后又出现：

```text
ModuleNotFoundError: No module named 'distro'
```

## 根因

shadow runner 为了干净性设置了独立 `HOME` 和 `CONAN_HOME`，但没有给 Python 保留真实用户下已安装的 Conan 依赖路径。`conan` 入口脚本能被 PATH 找到，但 import 依赖不完整，setup.sh 就尝试联网重装。

## 推荐做法

在自建 shadow runner 中区分：

- `HOME`、`CONAN_HOME`、`TMPDIR`、`TMPPREFIX`：使用每次 run 的隔离目录。
- `PATH`：包含 `$REAL_HOME/usr/local/bin`、`$REAL_HOME/.local/bin`、`/data/service/hnp/bin`。
- `PYTHONPATH`：包含 `$REAL_HOME/.local/lib/python3.12/site-packages` 和 `$REAL_HOME/usr/local/lib/python3.12/site-packages`。

先用同一套 `env -i` 探测：

```sh
env -i HOME="$RUN_HOME" \
  PATH="$REAL_HOME/usr/local/bin:$REAL_HOME/.local/bin:/data/service/hnp/bin:/bin:/usr/bin" \
  PYTHONPATH="$REAL_HOME/.local/lib/python3.12/site-packages:$REAL_HOME/usr/local/lib/python3.12/site-packages" \
  conan --version
```

## 验证证据

修正后，pico-sdk r4 setup 不再联网安装 Conan，直接输出 `Conan version 2.29.1` 并进入 L0/L1。