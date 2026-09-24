# E429 — 远古 libtool 的 shared 库丢失 DT_NEEDED；以及 conftest 运行期解析失效

## 错误特征

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: g_hash_table_new
    >>> referenced by .../p/lib/libprintsys.so
```
或运行期：
```
Error relocating libprintsys.so.1: g_list_prepend: symbol not found
Error loading shared library libglib-2.0.so.0: (needed by ./pcaptest)
```
共同特征：**构建本身成功**，`.so` 却只有 `libc.so` 一条 `NEEDED`，同时带着大量未解析外部符号。

## 触发条件
- 构建系统: autotools，且包内自带 1999–2002 年 libtool（存在 `ltconfig`，用 `AC_PROG_LIBTOOL`/`AM_PROG_LIBTOOL`，非 `LT_INIT`）
- 阶段: 下游链接期 / 运行期（不在本包构建期）
- 平台: OHOS（lld 默认 `--no-allow-shlib-undefined` + `--as-needed`，musl ld.so 严格按 NEEDED 加载）

## 根因
`ltconfig` 的 `archive_cmds='$CC -shared $libobjs $deplibs $linkopts …'` 只把 `$deplibs`
交给 linker，而它会把非系统搜索路径下的 `-lglib-2.0`/`-ltdb`（典型即 conan 包目录）
分类进 **`old_deplibs`** 而非 `$deplibs`，于是这些库**根本不进链接命令**。
构建 shared 库时未开 `--no-undefined`，故链接不报错，缺陷被推迟到消费者。
判据：同一 libtool 链接出的**可执行文件**（如 `bin/pcap`）NEEDED 是完整的，
只有 `.so` 缺失 —— 看到这个反差即可定性。

## 方案（relink，修产物本身）
在 `package()` 内用同批构建出的静态归档重建 `.so`：

```
<cc> -shared -Wl,-soname,libfoo.so.1 \
     -Wl,--whole-archive libfoo.a -Wl,--no-whole-archive \
     -Wl,--no-as-needed -L<glib>/lib -L<tdb>/lib -lglib-2.0 -ltdb -o libfoo.so.1.0.0
```
要点：①输入用 `.a` 而非 `.libs/*.o`（package 阶段 `.o` 已不存在）；②输入缺失必须
`raise`，**不可静默 return**（否则修复悄然失效、表现为下游随机失败）；③HMDFS 不能覆盖
符号链接，须先 `os.remove` 再 `os.symlink`（R9）；④修完把 `.la` 从包里删掉，其
`dependency_libs` 指向构建机绝对路径。

## 已验证无效的路线（勿重复）
1. 在依赖 flags 里加 `-Wl,--no-as-needed`：能进入 `GLIB_LIBS`/`LDFLAGS`/`LIBS`，但 `.so` 的 NEEDED 依旧不变。
2. 给 `src/Makefile.in` 补 `libprintsys_la_LIBADD=$(GLIB_LIBS)`：位置正确但仍不写 NEEDED。
3. 用 `cpp_info.sharedlinkflags/exelinkflags` 向下游传放宽参数：CMakeDeps 不传导，运行期照样失败，且把负担推给消费者。

## 同族教训：conftest 的运行期解析
`AM_PATH_GLIB` 一类老宏会**编译并运行**探测程序。实测：CI 上经 VirtualBuildEnv 注入的
`LD_LIBRARY_PATH` **并未到达该 conftest**，表现为 `The test program compiled, but did not run`；
给探测程序写 `-Wl,-rpath`（DT_RUNPATH 随二进制携带）后 CI 转绿。
两个必须注意的连带问题：
- 上游若写 `LDFLAGS=$(GLIB_LIBS)`，探测专用的 `-Wl,-rpath` 会**顺路烘进产物**（实测
  `bin/pcap` 的 RUNPATH 被写入构建机绝对路径）→ 必须在 configure 之后、make 之前从生成的
  `Makefile` 中剥离。
- 不要凭「本机通过」断定机制正确：本机 glib 恰好 `NEEDED` 只有 `libc.so`，会掩盖传导失效。

## 验证
```
llvm-readelf -d <pkg>/lib/libfoo.so.* | grep -E "NEEDED|RUNPATH"   # 依赖库必须在列，RUNPATH 不得含构建机路径
llvm-readelf -d <pkg>/bin/<tool>      | grep RUNPATH               # 与未注入探测 flag 的基线一致
conan create ... && <test_package>                                 # 10/10
```

## 影响范围
所有内嵌 1999–2002 年 libtool（包内有 `ltconfig`）、在 OHOS/lld 下构建 shared library
并被下游消费的 autotools 包。实测案例：libprintsys/0.6（PR #11146，CI #51352 失败 → #51993 通过）。
