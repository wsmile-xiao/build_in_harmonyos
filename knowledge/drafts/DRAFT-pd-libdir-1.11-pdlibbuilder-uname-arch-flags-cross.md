# draft-pd-libdir-1.11-pdlibbuilder-uname-arch-flags-cross

> Status: **Draft**（待审核 promote）| severity: `3` | category: `build|cross-compile` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-pd-libdir-1.11-pdlibbuilder-uname-arch-flags-cross.kv`

---

**匹配关键词**：pdlibbuilder, pd-lib-builder, arch.c.flags, -march=core2, -mfpmath=sse, -msse, uname -m,
PDINCLUDEDIR, PDLIBDIR, installpath, pd_linux, extension, Makefile.pdlibbuilder

## 症状

`pd-libdir/1.11` 用上游 `Makefile` + `Makefile.pdlibbuilder` 构建，用 CI 自带的
x86_64 Linux worker 交叉编译 OHOS aarch64 时，clang 直接拒绝编译：

```text
<OHOS clang> -DPD -I ".../include/pd" -DUNIX -fPIC -DVERSION='"1.11"' \
  -Wall -Wextra -Wshadow -Winline -Wstrict-aliasing -O3 -ffast-math -funroll-loops \
  -fomit-frame-pointer -march=core2 -mfpmath=sse -msse -msse2 -msse3 \
  -o libdir.o -c libdir.c
clang: error: unsupported argument 'core2' to option '-march='
make: *** [Makefile.pdlibbuilder:865: libdir.o] Error 1
```

（clang 在第一个错误即停；把 `-march` 去掉单独试 `-mfpmath=sse` 时，aarch64 clang 报的是
`error: unknown FP unit 'sse'`。）

## 根因

pd-lib-builder（`Makefile.pdlibbuilder` 0.4.4）用两个 `$(shell uname ...)` 推导构建配置。
**OHOS CI worker 的 `uname` 就是 `HarmonyOS`**，而 conan 交叉编译时「构建机 ≠ 目标机」：

1. **平台分支整体被跳过（真正的坑）**：`:467 uname := $(shell uname)`，`:469`
   `ifeq ($(findstring $(uname), Linux GNU GNU/kFreeBSD), $(uname)) system = Linux`。
   `HarmonyOS` 全串不命中 → `system` 为空 → `ifeq ($(system), Linux)` 整块（`:497-510`）被跳过：
   `extension` 为空、`c.ldflags` 的 `-rdynamic -shared -fPIC` 全丢、`c.ldlibs` 的 `-lc -lm` 也丢。
   于是产物名退化成 `libdir.`，链接按可执行文件走：

   ```text
   ++++ info: linking objects in libdir. for lib libdir
   /data/service/hnp/bin/clang   -Wl,-soname,libdir.pd_linux  -o libdir. libdir.o
   ld.lld: error: undefined symbol: main
   ld.lld: error: undefined symbol: sys_getversion
   ld.lld: error: undefined symbol: sys_register_loader
   ...（15 个 Pd 符号全报）
   clang-15: error: linker command failed with exit code 1
   ```

   **这条在本地根本复现不出来**：WSL2 开发机 `uname` 就是 `Linux`，会自动走对分支，一切正常。
   只有真机 worker 暴露——典型「环境语义不可迁移」，本地全绿 ≠ CI 全绿。
   本地要复现需伪造 `uname`：PATH 前置一个对 `-s` 返回 `HarmonyOS`、对 `-m` 返回 `aarch64` 的脚本。

2. **架构 flag**：`:438 machine := $(shell uname -m)`，`:457`
   `ifeq ($(findstring $(machine), ia64 x86_64), $(machine)) arch.c.flags = -march=core2 -mfpmath=sse -msse -msse2 -msse3`。
   x86_64 构建机必然命中，把 x86 专属 flag 塞给 aarch64 OHOS clang（硬编码架构字符串，不是按目标
   推导，所以 profile 的 `arch=armv8` 救不了它）。OHOS worker 是 aarch64 故不命中，但换 x86 构建机就会踩。

3. **头文件目录**：`:607 PDINCLUDEDIR ?= $(pdincludepath)`，而 `pdincludepath := $(wildcard /usr/include/pd)`
   在 worker 上为空 → 编译命令里 `-I ""` → `m_pd.h` 找不到。
4. **安装路径字符串直拼**：`:617 installpath := $(DESTDIR)$(PDLIBDIR)/$(lib.name)`，
   无分隔符拼接。写 `PDLIBDIR=lib` 会得到 `/tmp/outlib/libdir` 这种畸形路径，必须写 `/lib`。

## 推荐方案（`make-command-line-system=linux + clear-arch.c.flags + pdlibdir-leading-slash + pdincludedir-from-dep`）

不打平台补丁，在 make 命令行覆盖变量（上游 `Makefile` / `Makefile.pdlibbuilder` 保持原样）：

```bash
make CC="<profile 的 tools.build:compiler_executables.c>" \
     system=Linux \
     arch.c.flags= \
     PDINCLUDEDIR="<Pd 头文件目录>" \
     PDLIBDIR=/lib \
     lib.version=1.11 \
     LDFLAGS="-Wl,-soname,libdir.pd_linux" -j1
```

- **`system=Linux` 必需**：命令行变量优先级高于 Makefile 里的 `:=` 赋值，强制走 Linux 分支，
  拿到 Pd 查找的 `pd_linux` 后缀与 `-rdynamic -shared -fPIC`、`-lc -lm`。
- `arch.c.flags=` **传空值**清空。
- `CC` 从 profile conf 取（R33：不裸用 `${CC}`）；pd-lib-builder 默认是 `gcc`（`:580`）。
- `lib.version=` 让 `-DVERSION` 进二进制（`setup()` 会打印它），`LDFLAGS` 补 DT_SONAME。

### 修复前后实测对比（伪造 `uname` → HarmonyOS）

```text
修复前: linking objects in libdir.
        clang  -Wl,-soname,libdir.pd_linux  -o libdir. libdir.o
修复后: linking objects in libdir.pd_linux
        clang -rdynamic -shared -fPIC -Wl,-rpath,"$ORIGIN",--enable-new-dtags -Wl,-soname,libdir.pd_linux \
              -o libdir.pd_linux libdir.o -lc -lm
```

## 验证

`pd-libdir/1.11` 本地 conan create 全绿（22/22 断言通过）；缺 `arch.c.flags=` 时 100% 复现
`-march=core2` 报错；缺 `system=Linux` 时在伪造 HarmonyOS `uname` 下 100% 复现
`undefined symbol: main`。CI #66208 首次红灯即此根因（`conan-build-test` ❌，20s 内失败），
定位后加 `system=Linux` 修复。

---

*本文件由 `knowledge/drafts/DRAFT-pd-libdir-1.11-pdlibbuilder-uname-arch-flags-cross.kv` 字段派生；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
