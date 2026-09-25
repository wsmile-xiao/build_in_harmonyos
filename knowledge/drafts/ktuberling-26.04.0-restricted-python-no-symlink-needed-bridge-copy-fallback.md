# 受限沙箱域 python3 禁 symlink 系统调用：ELF 绝对路径 NEEDED 桥接的 copy2 兜底

> Draft: DRAFT-KTUBERLING-2604-RESTRICTED-PYTHON-NO-SYMLINK-NEEDED-BRIDGE-COPY-FALLBACK
> Stem: `ktuberling-26.04.0-restricted-python-no-symlink-needed-bridge-copy-fallback` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-KTUBERLING-2604-RESTRICTED-PYTHON-NO-SYMLINK-NEEDED-BRIDGE-COPY-FALLBACK
- **严重度**: 2
- **类别**: ohos-platform|packaging|elf|test-harness
- **触发工具**: conan|test_package|runtime-loader
- **阶段**: testing

## 错误特征

test_package 运行期（musl loader 阶段）：

```
Error loading shared library .../.cache/conan2/p/knews8e3b6e11174be/p/lib/libKF6NewStuffWidgets.so
  (needed by .../lib/libKDEGames6.so)
Error relocating .../lib/libKDEGames6.so:
  KNSWidgets::Button::dialogFinished(QList<KNSCore::Entry> const&) symbol not found
  KNSWidgets::Button::staticMetaObject symbol not found
```

conan 日志中先出现（根因现场，藏在 WARN 里）：

```
WARN: cannot create NEEDED fallback .../.cache/conan2/p/.../libKF6NewStuffWidgets.so:
  [Errno 13] Permission denied: '.../.conan2/p/.../libKF6NewStuffWidgets.so' -> '.../.cache/conan2/...'
```

## 根因链

1. 制品仓预编译二进制内嵌**构建机绝对路径** `~/.cache/conan2/p/<short>/p/lib/*.so`；
2. 本机 conan 缓存是默认 `~/.conan2` → 内嵌路径不原生存在，test_package 桥接逻辑
   （DT_NEEDED 扫描 + `os.symlink` 建链）出手兜路径；
3. **本机 cmd-pkgs python3 的沙箱域被平台策略禁 symlink 系统调用**——
   任意 src/dst 组合的 `os.symlink` 均 `[Errno 13]`，`ln` 二进制相同参数全部成功；
4. 桥接代码对建链失败仅 `warning` 后继续 → loader 重定位失败 → "symbol not found"。

表面症状（KNSWidgets 符号缺失）与根因（syscall 权限）相距两层，极易误诊为缺库。

## 诊断口诀：2×2 矩阵

| 组合 | 结果 |
|---|---|
| python `os.symlink` → 任意 dst | **EACCES（复现）** |
| python `os.symlink`，src=`/etc/hostname` → `.cache` | EACCES（排除 src 路径因素） |
| python `os.symlink` → `~/tmp` | EACCES（排除 dst 路径因素） |
| `ln -s` 相同参数 → `.cache` / `~/tmp` / `.conan2` | 全部 rc=0 |

ln 成功而 python 同参数失败 ⇒ **进程域限制**，不是路径/HMDFS/权限位问题。
CI 端 `/data/app/bin/python3`（另一域）不受限——kfourinline / kgoldrunner /
libktorrent 同机制先例 CI 全绿可证。

## 修复范式

```python
try:
    os.symlink(source, entry)
    fixes += 1
except OSError:
    # 受限沙箱域（本机 cmd-pkgs python3）禁 symlink；CI 端
    # /data/app/bin/python3 不受限。退化为实文件拷贝，与
    # _prepare_runtime_links 的 copy2 兜底同款。
    shutil.copy2(source, entry)
    fixes += 1
```

实文件拷贝对 loader 语义等价、不依赖 symlink 权限；CI 端 python 可
symlink，兜底不触发、行为不变。

## 附带陷阱：缓存布局决定走不走建链分支

- `CONAN_HOME=~/.cache/conan2`（与构建机同构）→ 内嵌路径原生存在，
  `os.path.exists` 短路，**完全不走建链分支**；
- `CONAN_HOME=~/.conan2`（CI worker 同构）→ 走建链分支。

同一天"绿跑"与"红跑"的差异可能只来自缓存布局切换，而非代码变更——
排查前先 `echo $CONAN_HOME` 并对齐基线。

## 来源

- PR #11760（ktuberling 26.04.0）本地全量 CI 复验，2026-09-22
- 修复 commit：`b1b63ca82`（test_package/conanfile.py `_fix_absolute_needed`）
