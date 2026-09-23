# E580 — Python 扩展模块后缀归一化：OHOS wheel 的 `-aarch64-linux-ohos.so` 需在 pip install 之后重命名为本机 EXT_SUFFIX

## 错误特征

封装 OHOS 社区 PyPI 源的预编译 wheel（tag `ohos_aarch64`）后，`import <pkg>` 立即失败：

```
ModuleNotFoundError: No module named 'yt.frontends.artio._artio_caller'
ImportError: cannot import name '_artio_caller' from 'yt.frontends.artio'
```

排查时可见：

```
$ python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"
.cpython-312.so
$ ls site-packages/yt/frontends/artio/
_artio_caller.cpython-312-aarch64-linux-ohos.so    # ← 与 EXT_SUFFIX 不一致
```

另一类症状出现在安装阶段：

```
ERROR: yt-4.4.2-cp312-cp312-ohos_aarch64.whl is not a supported wheel on this platform.
```

## 触发条件

- 构建系统: Python / pip（封装预编译 wheel，无 C/C++ 源码编译）
- 阶段: installation / runtime（`pip install` 之后、`import` 之时）

## 根因分析

1. **命名规则差异**：OHOS 社区源发布的 wheel 内，扩展模块按 PEP 425 完整平台标签命名，
   形如 `foo.cpython-312-aarch64-linux-ohos.so`；而设备本地 Python 的
   `EXTENSION_SUFFIXES` 仅为 `['.cpython-312.so', '.abi3.so', '.so']`（`SOABI=cpython-312`），
   导入器按 `EXT_SUFFIX` 拼接模块路径，因此找不到文件 → `ModuleNotFoundError`。
2. **pip 安装会还原后缀**：即使先把 wheel 内的文件改名，`pip install` 仍会按 wheel 记录
   （`RECORD`）还原成平台后缀写入 site-packages。**故归一化必须放在 `pip install` 之后**，
   在 wheel 打包阶段改名无效。
3. **平台 tag 不匹配**：本机平台 tag 为 `harmonyos_aarch64`（HNP Python）或
   `harmonyos-aarch64`，与社区 wheel 的 `ohos_aarch64` 不一致，pip 会拒绝本地安装 →
   必须用 `pip install --platform ohos_aarch64 --abi cp312 --only-binary=:all: --target <prefix>`
   显式指定目标平台绕过本地 tag 校验。

## 解决方案

### 推荐方案

在 Python 配方中，`pip install`（带 `--platform/--abi/--target`）之后追加一步归一化，
把 site-packages 下所有平台后缀的扩展改名为本机 `EXT_SUFFIX`；并在自检中断言后缀一致。

```python
# conanfile.py package() 内，pip install 之后
suffix_bad = "-aarch64-linux-ohos.so"
for p in Path(site).rglob(f"*{suffix_bad}"):
    p.rename(p.with_name(p.name.replace(suffix_bad, ".so")))
```

```bash
# 等价 shell 一行
find <prefix> -name '*.cpython-312-aarch64-linux-ohos.so' -exec sh -c \
  'for f; do mv "$f" "${f%-aarch64-linux-ohos.so}.so"; done' sh {} +
```

> 文件名前缀（`cpython-312`）必须与目标解释器的 `SOABI` 一致；跨 Python 小版本时
> 应改为按 `sysconfig.get_config_var('EXT_SUFFIX')` 动态生成目标名。

### 禁止做法

- ❌ **只在 wheel 解包阶段改名**：`pip install` 会按 `RECORD` 还原，白做。
- ❌ **软链到带平台后缀的名字**：HMDFS 下软链行为受限，且 `EXTENSION_SUFFIXES` 不含该
  后缀，导入器根本不会去查这个路径。
- ❌ **改本机 `EXTENSION_SUFFIXES` / `SOABI`**：污染全局解释器，影响所有 Python 包。

## 验证

```bash
# 1. 无残留平台后缀
python3 -c "import sys,sysconfig,glob,os; sfx=sysconfig.get_config_var('EXT_SUFFIX'); bad=[p for p in glob.glob(os.path.join(sys.prefix,'**','*.so'),recursive=True) if '-aarch64-linux-ohos' in os.path.basename(p)]; assert not bad, 'un-normalised OHOS extension suffix (local EXT_SUFFIX=%r): %r' % (sfx, bad)"

# 2. 扩展可实际加载
python3 -c "from yt.frontends.artio import _artio_caller; print(_artio_caller.__file__)"
```

## 关联条目

- 相关: E319（Python 网络与打包）、E512（Python 依赖与 CI 环境）、E581（依赖版本上限对齐）
