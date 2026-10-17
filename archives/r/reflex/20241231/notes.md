# reflex 20241231 适配笔记

> REFLEX = Thomas Dickey 维护的 flex 2.5.4 分支（"relocalizable fast lexical
> scanner"），上游 https://invisible-island.net/reflex/ 。
> 注意同名混淆：本包**不是** cespare/reflex（Go）也**不是** Genivia RE/flex
> （后者在仓内为 `archives/r/re-flex/`）。

## 编译环境

- 构建系统: autotools（VPATH 树外构建）
- 编译日期: 2026-09-29
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，`/data/service/hnp/bin/clang`）
- 目标三元组: `aarch64-linux-ohos`
- 状态: built

## 编译步骤

1. `tool_requires` 提供 `bison/3.8.2`（Makefile 中 `YACC = bison -y`）与
   `diffutils/3.12`（`make check` 依赖 `cmp`）。
2. configure（由 `AutotoolsToolchain` 生成，树外构建）：
   ```
   ./configure --prefix=/ \
       --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
       --disable-shared --enable-static
   ```
   `--build`/`--host` 必须显式给（见问题 #1）。
3. 应用补丁 0001（针对 `skel.c`），随后用 `os.utime` 把 `skel.c` 的 mtime 抬到
   `flex.skl` 之上（见问题 #2、#3）。
4. `make` → 产出 `flex`（安装期经 GNU 命名变换改名为 `reflex`）、`libfl.a`
   （→ `librefl.a`）、`FlexLexer.h`（→ `reFlexLexer.h`）、`reflex.1`。
5. OHOS 上 ELF 须携带 `.codesign` 才能执行（E077）→ 先对构建树里的 `flex`
   自签，`make check` 才跑得起来。
6. `make check`：自举回归 —— 用刚构建出的生成器重新生成 `scan.l` → `scan.c`，
   与发布包预生成的 `initscan.c`（由 `.bootstrap` 复制为 `scan.c`）逐字节比对。
   随后依次跑 6 种表压缩模式 `COMPRESSION=-Ce/-Cm/-f/-Cfea/-CFer/-l`。
7. `make install DESTDIR=<package_folder>`（`Autotools.install()`，prefix=/）。
8. 对安装出的 `bin/reflex`、`bin/reflex++` 再做一次签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | 发布包自带的 vintage `config.guess` 不认识 HongMeng 内核 | 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`；两者 canonical 后相等 ⇒ `cross_compiling=no` ⇒ `@no_cross@` 守卫打开，`make check` 才会真正执行 |
| 2 | 补丁打在 `flex.skl` 上后 `make check` 失败（diff 报 `yy_c_buf_p = NULL` vs `= (char *) 0`） | 发布包内 `skel.c` 与 `flex.skl` **内容不一致却 mtime 相同**（均为 `2025-01-01 05:56`）；mtime 相等时 make 不触发 `skel.c: flex.skl` 规则 ⇒ 真正生效的构建输入是发布版 `skel.c`（与 `initscan.c` 一致）。`skel.c` 写 `(char *) 0`，`flex.skl` 写 `NULL` | 撤销对 `flex.skl` 的修改（还原 `.orig` 字节与 mtime），改为对 `skel.c` 打补丁；并在 `build()` 用 `os.utime(skel.c)` 强制其比 `flex.skl` 新，防止 `mkskel.sh` 回写覆盖补丁 |
| 3 | `reflex++` 生成的 C++ 扫描器全部无法编译（10 处 `use of undeclared identifier 'yy_current_buffer' / 'yy_c_buf_p' / 'yy_init' / 'yy_start' / 'yyin' / 'yyout'`） | 骨架把 C-only 的 `static int yy_init_globals(void)` 与 `int yylex_destroy(void)` 排在 non-C++ 守卫区块（`%-` … `%*`）**之外**；C++ 模式下这两个名字是 `yyFlexLexer` 的成员而非文件级全局，故引用失败 | 补丁 0001：在 `yy_init_globals` 起始前与 `yylex_destroy` 收尾后插入 `%-` / `%*` 标记，把两个函数包进 non-C++ 区（C 路径输出逐字节不变） |
| 4 | 用 `reflex++ -o foo.cc foo.l` 时生成物缺 `#include <reFlexLexer.h>` | `src/main.c` 的 `outn()` 在打开输出文件**之前**就把该 include 写到 stdout，`-o` 重定向时被丢弃 | 改用 stdout 形式 `reflex++ -t foo.l > foo.cc`（已写入 recipe 知识与 test_package 的 C++ 端到端用例） |
| 5 | `make bigcheck` rc=2，报 `./flex: unknown -C option '/'` | 上游 `bigcheck` 首项是裸 `-C`，本版选项解析器把紧随其后的独立参数当作压缩后缀 | 属上游缺陷（非 OHOS 相关）；recipe 只驱动其余 6 种可用模式（全部 rc=0），并在 `test_package/MANIFEST.yml` 记录排除理由 |
| 6 | `conan download byacc` 报找不到包 | 早期误判依赖 | reflex 只需要一个 yacc，由 `bison/3.8.2` 提供（`YACC = bison -y`）；byacc 非必需 |
| 7 | **本地全绿、CI 间歇失败（#65023 失败 / #65046 通过）**：`./config.status: line 244: /storage/Users/currentUser/.cache/tmp/cslDeidH/subs.sed: Permission denied`，随后 `subs.frag`/`out`/`in`/`undefs.sed` 全部同样报错 → `install-man` 生成失败 → `L1_RESULT=fail` | CI worker 上该次构建进程的 `TMPDIR` 落在 **HMDFS 用户卷**（`$HOME/.cache/tmp`），而 `config.status` 用 `umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX"` 建临时目录后**立刻**往里重定向写文件 —— HMDFS 新目录的属主/权限元数据尚未生效，故第一次写入即 EACCES。`configure` 本身通过（其临时文件用法不同），仅 `config.status` 段失败，故日志看起来像"构建中途随机失败" | 双保险：① 补丁 0002 去掉 `umask 077` 依赖并在临时目录创建后显式 `chmod 700 "$tmp"`；② recipe 的 `_pin_tmpdir()` 在 `configure` 前把 `TMPDIR`/`TMP`/`TEMP` 钉到**经"写入刚建目录并回读"探针验证**的可写根（优先 `/data/storage/el2/base/cache`，即非 HMDFS 的 el2 缓存）。判据：**本次实测为间歇竞态，不是确定性必现** —— 同一份修复前代码 #65023 失败、#65046 通过；#65021 实为 `git-clone` 基础设施失败（`cannot exec 'git-remote-https'`，未跑到 `config.status`），不可当作"同点复现"证据。故不能用"重试"规避，也不能仅凭"同点复现"断言确定性；根因真实存在，须从根因消除（同踩坑清单 #30 族） |

## 源码修改

`patches/0001-skel.c.patch`（+3 行，`patch_type: bugfix`，**非平台专用**）：

在 `skel.c` 的骨架字符串数组里插入 3 个骨架标记：

- `"%-",` 于 `"static int yy_init_globals(void)"` 之前（约第 1379 行）；
- `"%-",` 于 `yy_init_globals` 体内 `"%% code for yylineno update goes here"`
  之后的空串之前（约第 1387 行）；
- `"%*",` 于 `yylex_destroy()` 收尾 `"}"` 之后（约第 1411 行）。

标记语义（`src/misc.c: skelout()`）：`%-` 起 "仅非 C++ 输出" 区，`%+` 起 "仅 C++ 输出"
区，`%*` 恢复无条件输出，`%%` 终止骨架。补丁仅改变 C++ 路径，C 路径输出不变。

`patches/0002-configure-hmdfs-tmpdir.patch`（`patch_type: portability`，平台专用）：

`configure` 里即将写入 `config.status` 的临时目录段落：

```sh
# Create a (secure) tmp directory for tmp files.
: "${TMPDIR=/tmp}"
{
  tmp=`(umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX") 2>/dev/null` &&
  test -n "$tmp" && test -d "$tmp"
}  ||
{
  tmp=$TMPDIR/cs$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} ||
```

改为去掉 `umask 077` 依赖，并在块后补一行 `chmod 700 "$tmp" 2>/dev/null || true`。
`mktemp -d` 本来就会申请 `0700`，补丁只是让这个权限位在 HMDFS 上**确定生效**
（不再依赖 umask 与文件系统元数据的落地时序），安全语义不变。

## 依赖版本

| 类型 | 组件 | 版本 | 说明 |
|------|------|------|------|
| tool_requires | bison | 3.8.2 | 提供 `bison -y` 作为 YACC |
| tool_requires | diffutils | 3.12 | `make check` 的逐字节比对 |
| 编译工具 | clang / clang++ | 15（OHOS SDK 26.0.0.18） | 由 profile 的 `tools.build:compiler_executables` 指定 |
| 运行期 | — | — | 无外部依赖（`librefl.a` 自足） |

## 验证结果

```bash
# 1) 上游自举回归 + 6 种压缩模式（均在构建树内）
make check                                  # rc=0  "Check successful"
for m in -Ce -Cm -f -Cfea -CFer -l; do
    rm -f scan.c && make COMPRESSION=$m check   # 全部 rc=0
done
# 注：make bigcheck 在上游即失败（裸 -C），见问题 #5

# 2) 工具与产物完整性
reflex --version      # → reflex 2.5.4 / 20241231
reflex++ --version
test -f include/reFlexLexer.h && grep -c 'class yyFlexLexer' include/reFlexLexer.h
test -f lib/librefl.a && nm -g lib/librefl.a | grep -w yywrap

# 3) C 端到端（消费者视角）
reflex -o consumer.c consumer.l
clang -I"$PKG/include" consumer.c -L"$PKG/lib" -lrefl -o consumer
./consumer  # 输入 "42 alpha 7 _b9" → NUM:42 ID:alpha NUM:7 ID:_b9

# 4) C++ 端到端（消费者视角，必须用 -t stdout 形式）
reflex++ -t consumer.l > consumer.cc        # 首行即 #include <reFlexLexer.h>
clang++ -std=c++17 -I"$PKG/include" consumer.cc -L"$PKG/lib" -lrefl -o consumer
./consumer  # 与 C 路径同一词法流
```

以上 1–4 全部通过，对应 `test_package/` 的 7 项检查与 recipe `build()` 内的
上游测试驱动。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/reflex` | 词法分析器生成器主程序（已签名） |
| `bin/reflex++` | C++ 模式入口（`reflex -+` 同义词，已签名） |
| `lib/librefl.a` | C 运行时静态库（提供 `main()` / `yywrap()` / `yy_flex_*`） |
| `include/reFlexLexer.h` | C++ 基类声明（`FlexLexer` / `yyFlexLexer`） |
| `share/man/man1/reflex.1` | 上游 manpage |

## 注意事项

1. **同名陷阱**：本包是 Dickey 的 REFLEX（版本号是日期式 `20241231`）。
   `cespare/reflex`（Go）的版本恰好是 0.3.2；Genivia RE/flex 在仓内为
   `archives/r/re-flex/`。三者谱系不同，勿混。
2. **C++ 消费者必须用 `-t`**：`reflex++ -o out.cc` 会丢掉 `reFlexLexer.h` 的
   include 行（见问题 #4），生成物无法编译。
3. **补丁依赖 mtime 确定性**：`_force_patched_skeleton()` 的 `os.utime` 不是
   可选的锦上添花 —— 去掉它会让 `mkskel.sh` 在并行/增量构建下回写 `skel.c`，
   使 C++ 修复时有时无。
4. `make check` 是自举回归而非单元测试：它证明"生成器能稳定复现自己的扫描器"，
   真正的消费者可用性由 `test_package` 的 C/C++ 端到端用例覆盖。
---

**编译结束**: 2026-09-29 22:09
**最终状态**: built
