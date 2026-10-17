# E714 — 手写 Makefile 字面量陷阱与 make 调用行全钉法

- **状态**：DRAFT（`knowledge/drafts/DRAFT-E714-raw-makefile-literal-pin.kv` 配对）
- **取号**：`E714`（2026-09-24 `tools/knowledge_id.py --claim --task psignifit-2.5.6`，回查未占用）
- **实测来源**：psignifit 2.5.6 移植（任务卡 9786）；同族先例 samhain / aa3d / meschach（止损先例集 #4「CFLAGS 钉死」、#7「裸命令名」、#9「rc=0 假绿」）

## 现象（三个坑同框，psignifit `psig-src/Makefile` 实测）

```make
CYGFLAG =
DBFLAG  = -g
OUTDIR  = ~/bin      # ← 产物目录写死到 HOME
CC = gcc             # ← 设备/CI 无 gcc
LD = gcc $(CYGFLAG) $(DBFLAG)
LDFLAGS =            # ← 空：不带 -lm
CFLAGS = $(CYGFLAG) $(DBFLAG)   # ← -g，无优化
```

对应故障：`gcc: not found`（或 `cc: command not found`）→ `No such file or directory: <HOME>/bin/xxx` → `undefined reference to 'sqrt'/'exp'`。

## 关键机理：环境变量推不动文件级赋值

make 的优先级是 **命令行 > 文件 > 环境**（除非 `-e`）。所以 `export CC=clang`、`CFLAGS=... make` 对
`CC = gcc` 这种文件赋值**无效** —— 这正是 R33「绝不读 shell 环境变量」的另一面：
既不能依赖环境注入，也不会被环境污染，**唯一确定的注入点是 make 调用行**。

## 修法：一次调用行全钉（先例4「双钉」在无 configure 形态的对应物）

```bash
mkdir -p "$SRC/bin"
make -j1 gnu \
  CC="$CC" LD="$CC" \
  CFLAGS="-O2 -pipe -DNDEBUG" CXXFLAGS="-O2 -pipe -DNDEBUG" \
  CYGFLAG= DBFLAG= \
  LDFLAGS="-lm" \
  OUTDIR="$SRC/bin" \
  -C "$SRC/psig-src"
```

要点：

| 变量 | 为什么要钉 |
|---|---|
| `CC` / `LD` | 上游写死 `gcc`；设备/worker 无 gcc（先例7）。`CC` 从 `self.conf.get("tools.build:compiler_executables")` 取 |
| `CFLAGS` / `CXXFLAGS` | **编译旗标钉**：吃掉 `-g` 默认值并钉 `-O2 -pipe -DNDEBUG`（R33） |
| `LDFLAGS` | **链接旗标钉**：上游漏 `-lm`（Debian 靠补丁加 `LIBS=-lm`） |
| `CYGFLAG=` / `DBFLAG=` | 上游把调试旗标拆在两个变量里，留空防 `-g` 泄漏 |
| `OUTDIR` | `~/bin` 会把产物写进构建机 `$HOME`，且目录常不存在导致链接失败 |
| `-j1` | R9；conan 取 `os.cpu_count()`=20 而 affinity=8（§一.7），禁止超订 |

## rc=0 之后必须核产物（先例9）

`make` 返回 0 ≠ 产物存在（尤其 `OUTDIR` 目录没建成时可能走了别的分支）：

```python
if not os.path.isfile(os.path.join(outdir, "psignifit")):
    raise ConanException("make 返回 0 但产物缺失")
```

## 预扫描（prescan_pattern）

```
^\s*(CC|LD|OUTDIR|CFLAGS|LDFLAGS)\s*\+?=
```

命中 → 进入 `pin-all-make-variables-on-call-line` 路径；若变量被 `override` 或经 wrapper 调 make（调用行不可达），退回包内补丁改字面量，并走补丁三关（NUL=0 / `@@`≥1 / 真 apply 后 `cmp` 逐字节一致）。

## 禁用修法

1. `export CFLAGS=...` —— 对文件级赋值无效，制造"已修复"错觉。
2. `make -j$(nproc)` —— 超订（nproc=8 与 conan 的 20 不一致，失败形态像配方错）。
3. 放大 `OUTDIR` 到系统目录（如 `/usr/bin`）—— 触发 PF6 前缀闸与权限问题。
