# E544-draft-6EE2 — OHOS libc.a 比 libc.so 多导出 ~380 个符号：-static 探针掩盖交付动态构建的 undefined symbol

## 症状

- x86_64 runner 上为了拿到运行证据，用 `-static` 交叉构建 + qemu-user binfmt 跑功能测试：编译、链接、测试全部通过。
- 同一份源码走 `conan create`（仓库 profile，默认动态链接）：

```
ld.lld: error: undefined symbol: rindex
>>> referenced by hexbin.c ...
clang-15: error: linker command failed with exit code 1
make[1]: *** [makefile:36: hexbin] Error 1
```

## 根因

OHOS NDK sysroot（`sysroot/usr/lib/aarch64-linux-ohos/`）里 `libc.a` 与 `libc.so` 的导出表不一致：

| 对象 | 全局符号数 |
|---|---|
| `libc.a`（`llvm-nm --defined-only -g`，T/W） | 2319 |
| `libc.so`（`llvm-nm -D --defined-only`） | 1592 |
| 仅在 `libc.a`、且不以 `_` 开头 | 380 |

仅静态可用的遗留接口包括：`rindex getw cuserid ecvt fcvt gcvt getpass lchmod stime setkey encrypt`。
`<strings.h>` 只声明 `index`，不声明 `rindex`。

K&R 代码（`-std=gnu89`，隐式声明只是告警）或自带 `extern char *rindex();` 的代码能编译过去，
问题只在链接期暴露；而 `-static` 链接会从 `libc.a` 取到符号，所以本地静态探针看不出来。

## 方案

1. **优先走上游已有的 POSIX 分支**：macutils 的 `hexbin/globals.h` 在 `#ifdef BSD` 下用 `rindex`，否则用 `strrchr`；
   `fileio/wrfile.c`、`util/curtime.h` 的非 BSD 分支用 `memcpy/memset`、`<time.h>`。
   配方里把上游 makefile 的 `CF` 去掉 `-DBSD` 即可，零补丁。
2. 没有现成分支时，补丁改用标准接口（`rindex`→`strrchr`、`ecvt/fcvt/gcvt`→`snprintf` 等）。
3. **验证顺序**：先让默认（动态）配置的 `conan create` 链接通过，再对**同一批 `.o`** 追加 `-static` 只重链做 qemu 运行
   （macutils：删掉 7 个工具二进制后以 `CF=... -static` 重跑 make，make 只重新链接，不重编）。两者都过才算打通。

## 禁止

- 为了链过把整个交付包改成 `-static`（如 `tc.extra_ldflags.append("-static")`）：只是绕开导出表差异，偏离仓库默认动态链接约定。
  只在构建机上运行、不进包的生成器（macutils 的 `CC_FOR_BUILD="<clang> -static"` 构建 `makecrc`）不受此限。
- 把「-static 探针 / qemu 测试通过」当成「交付的动态构建没问题」。

## 验证命令

```bash
NDK=/opt/command-line-tools/sdk/default/openharmony/native
S=$NDK/sysroot/usr/lib/aarch64-linux-ohos; NM=$NDK/llvm/bin/llvm-nm
$NM -D --defined-only $S/libc.so | grep -cw rindex      # 0
$NM --defined-only $S/libc.a | grep -cw 'T rindex'      # 1
```

## 查重

- `DRAFT-cconv-0.6.3-rindex-strrchr` / `DRAFT-irqbalance-1.9.4-rindex-strrchr` / `DRAFT-rdma-core-61.0-rindex-strrchr` /
  `DRAFT-motif-2.3.8-musl-no-rindex-xpm-guard`：都记录了「OHOS libc 无 rindex → 改 strrchr」的单点修复，
  但都没有指出 **`libc.a` 有而 `libc.so` 没有**，也没有指出**静态探针会掩盖问题**。
- `E430-draft-4235`：libtool 吞掉 `-static` 导致本地 qemu 跑不了，方向相反（静态没生效），不覆盖本条。
- 本条新增：导出表差集的量化（380 个）与遗留接口清单、「静态探针 ≠ 动态交付」的验证顺序，以及优先走上游 POSIX 分支的零补丁处置。

## 来源

macutils 2.0b3 适配（`archives/m/macutils/2.0b3/notes.md`）。
