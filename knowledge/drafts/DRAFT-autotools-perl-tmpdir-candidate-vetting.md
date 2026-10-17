# DRAFT-autotools-perl-tmpdir-candidate-vetting — autoheader 因 Perl 临时目录判定失败而静默 exit 1

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-14 | Severity: 🟡 medium
> Source: libiodbc2 3.52.16（`archives/l/libiodbc2/3.52.16`）W3/finish 引导链失败链

## 相关既有条目（同族差异化定位）

| 既有条目 | 问题面 | 本条增量 |
|---|---|---|
| E114 / E112 | HMDFS `umask 077` 使 `config.status` 临时目录不可写（owner 也不可写） | 本条不是权限位问题，而是 **Perl 的 stat 型权限判定** 在 uid 映射挂载上恒为假，导致 TMPDIR 候选被静默丢弃 |
| DRAFT-coinor-vol-1.5.4-tmpdir-writable-probe-fallback | TMPDIR 候选**不可写/不存在** → clang 无法建临时文件 → `C compiler cannot create executables` | 本条候选**可写**且 clang 正常；失败者是 **Perl 工具**（autoheader），症状是 `missing template` 噪音 + exit 1，与可写性无关 |
| E002 | OHOS `/tmp` 为只读，建议 TMPDIR 指向可写目录 | 本条指出「可写」不充分，还需 **Perl 可见** |

**撞车判定**：全库检索 `File::Spec.*tmpdir`（0 命中）、`config.hin`（0 命中）、
`missing template`（0 命中）。与 coinor-vol 草稿同属 TMPDIR 主题但失败语义不同，
作为**姊妹条目**申报并在正文互相引用。

## Symptom

`conan create` 的 `build()` 在 autotools 引导链第 3 步失败（libtoolize / aclocal 均正常）：

```text
libiodbc2/3.52.16: RUN: "/data/service/hnp/bin/autoheader"
autoheader: warning: cannot read /storage/.../b/ahRkqgub/config.hin: Not a tty
autoheader: warning: missing template: HAVE_DLOPEN
autoheader: warning: missing template: HAVE_WCHAR_H
... （configure.ac 里每个 AC_DEFINE 一条）
autoheader: warning: missing template: const

libiodbc2/3.52.16: ERROR: Error in build() method
  while calling '_bootstrap_autotools', ... ConanException: Error 1 while executing
```

`include/config.h.in` **始终不生成**，因此后续 `automake`（`required file 'admin/ltmain.sh' not found`）、
`config.status`（`cannot find input file: 'Makefile.in'`）接连失败——这些都是**次生现象**，
首个真实错误只有那一行 `cannot read <tmp>/config.hin`。

## Root Cause

1. `Autom4te::General` 用 `File::Spec->rel2abs(File::Spec->tmpdir())` 决定 `$tmp`；
   `File::Spec->tmpdir()` 逐个丢弃 `-d`/`-w` 判定失败的候选，**全部失败时回退当前目录**。
2. OHOS worker 上构建树位于 uid 映射挂载（本机 `/storage/Users/...`：`stat` 报告属主
   20001006，而会话 uid 为 20020178，`chmod` 不生效、`chown` 不可用）。该挂载上
   Perl 的 stat 型权限判定恒为假：

   ```text
   $ stat -c '%a %U' /storage/.../tmp/rtest.txt   # 660 20001006 file_manager
   $ perl -e 'print -r $ARGV[0]' /storage/.../tmp/rtest.txt   # 0（shell test -r 与 python os.access 均为真）
   ```

   于是配方设定的 `TMPDIR=<build_folder>/tmp` 被丢弃，回退到 cwd（同一挂载）→ 同样不可读。
3. `autoheader` 在 `$tmp` 下写好 `config.hin` 后，用 `if (! -r $template)` 校验自己刚写的文件
   → 判定失败 → 一个符号都无法从模板中删除 → 所有 `AC_DEFINE` 报 `missing template`
   → `exit 1 if keys %symbol` **在 `update_file("$tmp/config.hin", "$config_hin")` 之前退出**，
   `include/config.h.in` 永不落盘。

对照实验（决定性）：同一份最小 `configure.ac`（`AC_CONFIG_HEADERS` + 2 个 `AC_DEFINE`）

| 工程所在目录 | autoheader rc | include/config.h.in |
|---|---|---|
| `/storage/Users/currentUser/tmp/...`（uid 映射） | **1**（全是 missing template） | 未生成 |
| `/data/storage/el2/base/cache/...`（进程自有 uid） | **0** | 正常生成 |

探针复现（判定某候选是否会被 Perl 采纳）：

```sh
perl -e 'exit(-d $ARGV[0] && -w $ARGV[0] ? 0 : 1)' "$candidate"; echo "rc=$?"
# rc=0 → File::Spec 会保留；rc≠0 → 被丢弃并回退 cwd
```

## Recommended Solution

### 主方案：TMPDIR 候选加 Perl 判定探针（conan 配方内）

`_prepare_tmpdir()` 保留 `<build_folder>/tmp` 为首选，但先用探针校验；不被接受时回退环境候选：

```python
def _perl_usable_tmpdir(path):
    perl = shutil.which("perl")
    if not perl:
        return True                      # 无 perl 时不做额外限制
    import subprocess
    probe = subprocess.run(
        [perl, "-e", "exit(-d $ARGV[0] && -w $ARGV[0] ? 0 : 1)", path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return probe.returncode == 0

def _prepare_tmpdir(self):
    candidates = [os.path.join(self.build_folder, "tmp")]
    candidates += [os.environ.get(v) for v in ("TMPDIR", "TMP", "TEMP")]
    for cand in candidates:
        if not cand:
            continue
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            continue
        if os.access(cand, os.W_OK) and _perl_usable_tmpdir(cand):
            tmpdir = cand
            break
    else:
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
    for var in ("TMPDIR", "TMP", "TEMP"):
        os.environ[var] = tmpdir
    return tmpdir
```

要点：
- **在正常 worker 上探针为真 → 与不探针的原实现行为完全一致**，不改变既有通过包的构建路径；
- 候选顺序保持 `build_folder/tmp` 优先，避免把构建临时文件散落到环境共享目录；
- 最后仍退回 `build_folder/tmp`，使失败时给出明确错误而非静默用 `/tmp`。

### 回退方案

若不愿引入探针：先把「环境已有且可写的 TMPDIR」置于 `build_folder/tmp` 之前。
在环境 TMPDIR 同样落在 uid 映射挂载的 worker 上仍会失败，故不如主方案稳妥。

### 禁止

- `sed -i`/patch 宿主 Perl 的 `File/Spec/Unix.pm`：宿主工具链非任务自有状态，污染并发构建；
- 对构建树 `chmod -R a+rwx`：uid 映射挂载忽略 `chmod`，且放宽权限修不了 stat 型判定。

## 单库实证

- 归档：`archives/l/libiodbc2/3.52.16`（iODBC 3.52.16，autotools，零第三方依赖）
- 改动前：`autoheader` rc=1，`include/config.h.in` 未生成，`conan create` 在引导链第 3 步失败；
- 改动后（本机同样环境）：`autoheader` rc=0、`include/config.h.in` 生成，
  引导链推进到 `automake` → `autoconf` → `configure` 全部执行；
- 本机最终仍被**另一类** worker 缺陷拦住（会话沙箱注入的 `rm` 垫片 shebang 失效、
  子进程执行 `/bin` 符号链接偶发 EACCES → `libtoolize` 内 `/usr/bin/sed: inaccessible or not found`），
  属环境问题、非本条目范畴；`.ci-result.json` 未产出，W3 需在环境正常的 worker 上复跑。
