# DRAFT-pd-creb-conan2-compiler-executables

> Contributor: pd-creb 0.10.0 adaptation | Status: Draft | Updated: 2026-10-04
> Source: archives/p/pd-creb/0.10.0

## Symptom

The first `pd-creb/0.10.0` recipe built with

```python
self.run(f"make -j1 {make_vars}", env="conanbuild", cwd=self.source_folder)
```

and `conan create` came back green with all tests passing — while the packaged
objects were **x86-64**, not aarch64. Raising the parallelism to `-j32` finally
surfaced the real error:

```
ld.lld-15: error: unable to find library -lstdc++
make: *** [pd-lib-builder//Makefile.pdlibbuilder:881: biquadseries~.pd_linux] Error 1
```

## Root Cause

Two independent defects stack up.

**(1) Nothing puts the OHOS toolchain into `CC`/`CXX`.** The profile carries it
only as conf:

```ini
[conf]
tools.build:compiler_executables={"c": "/opt/lpk-fixed/clang", "cpp": "/opt/lpk-fixed/clang++"}
```

Three measurements, all with `-pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl`:

| recipe | result |
|---|---|
| no generator | `CC=[]`, `which cc → /usr/bin/cc`, `cc -dumpmachine → x86_64-linux-gnu` |
| `VirtualBuildEnv(self).generate()` | `CC=[] CXX=[] AR=[] STRIP=[] RANLIB=[]` |
| `buildenv_info.define("user","CC",…)` before/after the generator | `CC=[]` |

Listing the generators folder shows why: only
`conanbuildenv-release-armv8.sh` exists — the aggregated `conanbuild.sh` that
`env="conanbuild"` loads is produced by `conan install`, not by `conan create`.

So `make` sees an empty `CC` and falls back to `/usr/bin/cc`. `uname` still says
Linux, therefore pd-lib-builder still selects `extension = pd_linux`,
`pkglibdir = /usr/lib/pd-externals`, `-DUNIX`, and every path assumption holds.
The build "succeeds" and produces host objects.

**(2) pd-lib-builder hardcodes the GNU C++ runtime.** Inside
`ifeq ($(system), Linux)`:

```make
cxx.ldflags := -rdynamic -shared -fPIC -Wl,-rpath,"\$$ORIGIN",--enable-new-dtags
cxx.ldlibs  := -lc -lm -lstdc++
```

OHOS ships libc++ only, so the three C++ externals (`blosc~`,
`filterortho~`, `biquadseries~`) cannot link. Paradoxically this error is
useful: it is what exposed (1).

## Rec_approach

Read the toolchain from conf and put it **on the make command line** — command
line variables beat every makefile assignment, including pd-lib-builder's
unconditional `CFLAGS = …`:

```python
def _compiler(self):
    executables = self.conf.get("tools.build:compiler_executables", default={})
    cc, cxx = executables.get("c"), executables.get("cpp")
    if not cc or not cxx:
        raise ConanException(...)      # never fall back to the host
    return cc, cxx

def _make_vars(self):
    cc, cxx = self._compiler()
    return " ".join([
        f'CC="{cc}"', f'CXX="{cxx}"',
        f'PDINCLUDEDIR="{self._pd_include_dir()}"',
        'cxx.ldlibs="-lc -lm"',        # drop the hardcoded -lstdc++
    ])
```

The C++ runtime itself is attached by the toolchain driver (the local shim
appends `libc++abi.a libc++.a -lunwind`; the CI NDK driver does it natively), so
the recipe must not add `-lc++` itself.

Two more pd-lib-builder traps in the same family:

* `PLATFORM=aarch64-linux-ohos` is **not** usable — it triggers
  `export CC = $(PLATFORM)-gcc`, which does not exist (Error 127).
* `PDDIR` must **not** be set: `ifdef PDDIR` re-derives
  `PDINCLUDEDIR := $(wildcard $(PDDIR)/src)`. Pass only `PDINCLUDEDIR`.

## Prevention

* Any recipe that shells out to `make` without a Conan toolchain generator
  should first prove `echo CC=$CC` is non-empty. Never trust `rc=0`.
* Lock the product architecture down in `test_package`
  (`e_machine == EM_AARCH64`, `DT_NEEDED` must contain musl `libc.so` and must
  never contain glibc's `libc.so.6`/`libm.so.6`) so a host build can never pass
  again. That is exactly what
  `archives/p/pd-creb/0.10.0/test_package/test_pdcreb.py` does — 784
  assertions, no cross binutils required.
* Seeing `unable to find library -lstdc++` is a signal about *hardcoded GNU
  runtime names*, not about the toolchain. Cover it with a make variable; do not
  swap in `-lc++`.

## Related finding — Debian `a:b` patches vs Conan `patch_ng`

Independent of the toolchain issue, the six Debian patches failed to apply:

```
patch_ng: source/target file does not exist:
  --- b'pd-creb.orig/modules/bdiag~.c'
  +++ b'pd-creb/modules/bdiag~.c'
```

Conan's `patch()` defaults to `strip=0` and `apply_conandata_patches()` does not
change it, while Debian ships `pkg.orig/` → `pkg/` prefixes. Rather than relying
on a per-entry `strip:`, the patches were regenerated mechanically:

```bash
diff -u --label "a/$rel" --label "b/$rel" before/$rel after/$rel
```

and equivalence was *proved*, not assumed:

```
diff -r <tree patched with Debian originals via patch -p1> \
        <tree patched with the regenerated series>
→ EQUIVALENT: regenerated patches reproduce Debian's patched tree exactly
```

Always machine-generate patch headers (`diff -u --label`) — a hand-written
unified diff whose description block lacks a trailing newline silently merges the
`--- a/<file>` line and makes `patch_ng` skip the hunk with no error.
## Related finding — 不要把本地 driver 的链接模型当平台属性

同一个包在本地和 CI 的 **C++ 运行时链接模型不同**：

- 本地 profile 的 driver shim 静态附 `libc++abi.a` + `libc++.a`；
- CI profile 的 NDK driver（`/data/service/hnp/bin/clang`）动态链接 `libc++_shared.so`。

第一版测试硬断言 `DT_NEEDED == ["libc.so"]`，于是本地 692/0 全绿、CI 686/6 挂掉
（3 个 C++ 外部对象各 2 条）。这类"本地绿、CI 红"里，**先怀疑测试里的平台假设**
比先怀疑配方更常见。修法是断言两种 driver 共有的平台属性（musl `libc.so` 必在、
glibc 拆分运行时必不在），并接受 C++ ABI 符号前缀（`_Z*`/`__gxx_*`/`__cxa_*`/
`_Unwind_*`）由 `libc++_shared.so` 提供。

验证手法值得复用：**本地照抄 CI 的 driver 行为**（这里另建一个链接期追加
`-lc++_shared` 的 shim）跑完整 `conan create`，等于在推 CI 之前就把 CI 的失败条件
复现出来，比等一轮 CI 快得多。
