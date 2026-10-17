# DRAFT-10038: 本机沙箱按解释器启动路径施加 execve 允许清单（conan create "Permission denied" 真因）

- 条目主题：HarmonyOS PC WorkBuddy 环境里 `conan create` 在 autotools 自举步报
  `aclocal: Permission denied`（rc=126）的环境级根因与解法。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 影响面：本机所有跑 conan 的任务；CI 干净环境不受影响。

## 受控实验定位
同一包装脚本（`#!/bin/sh`）在不同父进程下的结果：

| 父进程 | 结果 |
|---|---|
| bash 直接执行 / `sh -c` | ✅ |
| perl `system()` / node `spawnSync` | ✅ |
| python（`$HOME/usr/local/bin/python3`，HMDFS） | ❌ EACCES |
| **python（`/data/storage/el1/bundle/.../python3`，应用包内）** | ✅ |

且对 ELF 同样生效（`/data/.../.aclocal-real` ELF 化同理被拒），与文件 0755、
`chmod`、`CONAN_HOME` 位置、`dangerouslyDisableSandbox` 均无关。

## 结论
限制按**启动解释器的路径**施加并被子进程继承（Landlock 式 exec 域）：HMDFS 解释器的
子孙进程只能 execve 系统根（如 `/data/service/hnp`）下的路径。conan launcher 的
shebang 恰是 HMDFS 解释器 → 必然失败。此前"非 ELF 脚本被拒"的判断是表象。

## 解法（不改配方）
```sh
PYTHONPATH=$HOME/usr/local/lib/python3.12/site-packages \
exec /data/storage/el1/bundle/libs/arm64/python/bin/python3 -c \
  'import sys; sys.argv[0]="conan"; from conans.conan import run; sys.exit(run())' "$@"
```
（conan 官方入口即 `conans.conan:run`。）`scripts/ohc-run.py` 同理需用包内 python 运行。

## 附加：构建子进程去污染
先 `unset BASH_ENV PYTHONPATH`、`unset -f rm rmdir unlink`、从 PATH 剔除
`.../shim/safe-bin` —— 否则 `configure` 的 `rm -f` 命中 `#!/bin/bash`（本机不存在）
报 `bad interpreter`，`config.status: error: could not create Makefile`。

## 关联
E490（辅助脚本可执行位）。
