# ocamlopt 烘焙首位 -L × lld 目录内 .so→.a 选择：系统静态归档影子化 conan 共享库，应以绝对路径显式链接供给 .so（-L 顺序修复无效）

## 场景

lablgtk3 3.1.5（OCaml GTK3 绑定）适配 HarmonyOS PC（aarch64，lld 15）。
conan 图内 glib 共享库一切就绪，但 dune 驱动的 ocamlopt 原生链接阶段
（`src/tools/gdk_pixbuf_mlsource.exe` 等可执行）在权威 CI round-02 链接失败。
这是该设备一切「ocamlopt 原生码 × conan 共享库」组合都可能命中的工具链语义问题，
不限 lablgtk3。

## 现象

`ci/round-02/build_and_test.log:5628-5644`（真实链接行 + 失败点）：

```text
# :5628 dune 驱动的 ocamlopt 原生链接命令行（节选）
(cd _build/default && .../p/bin/ocamlopt -w -40 -g -o src/tools/gdk_pixbuf_mlsource.exe
  .../lib/ocaml/unix.cmxa ... src/lablgtk3.cmxa ...)
# :5629 起
ld.lld: error: undefined symbol: ffi_type_void
>>> referenced by gclosure.c:0 (...)
>>>               gclosure.c.o:(g_cclosure_marshal_generic) in archive /storage/Users/currentUser/usr/local/lib/libgobject-2.0.a
ld.lld: error: undefined symbol: ffi_type_pointer
>>>               gclosure.c.o:(g_cclosure_marshal_generic) in archive /storage/Users/currentUser/usr/local/lib/libgobject-2.0.a
...
```

关键自证点：lld 报出的**供给者归档绝对路径就是系统目录静态库**——
`libgobject-2.0.a` 被 lld 选中供给 g_object 符号，而它自身依赖的 `ffi_*` 无供给。

## 根因

1. **ocamlopt 把固定 -L 烘焙在链接行首位**。`ocamlopt -verbose` 实测（任一新 shell）：
   驱动器拼出的 clang 链接行里 `-L/storage/Users/currentUser/usr/local/lib` 排在
   **第一位**，先于 stdlib 自身的 -L——这是工具链配置期烘焙进驱动器的，配方无法改序。
2. **lld 按目录顺序解析、目录内先 .so 后 .a**。首位目录恰存另一套 glib 2.88 构建的
   **静态归档**（`libglib/gobject/gio/gmodule/gthread-2.0.a`、`libintl.a`，无同名 .so）。
   于是 `-lgobject-2.0` 类裸名在首位目录被解析到 .a——即使 -L 列表靠后有 conan glib
   包的 `libgobject-2.0.so` 也轮不到它。
3. **影子归档暴露自身缺口**。静态 `libgobject-2.0.a` 的成员（gclosure.o 等）引用
   `ffi_type_void/ffi_type_pointer/ffi_prep_cif/ffi_call`（libffi 侧）与 `pcre2_*`，
   而链接行上没有任何输入供给它们 → `undefined symbol`。
4. **"-L 顺序修复不够"（关键反直觉发现）**。即使把 conan libdir 排到 -L 列表最前，
   工具链烘焙的首位 `-L<系统目录>` 仍恒在其前，裸名 `-l` 在那里就被同名 .a 截走。
   唯一正解是绕过「搜索」语义本身：**把供给 .so 以绝对路径列为显式链接输入**。

## 修复

`conanfile.py` `generate()`（round-04 PASS 实装）：

```python
explicit_inputs = []
for name in ("gio-2.0", "girepository-2.0", "glib-2.0",
             "gmodule-2.0", "gobject-2.0", "gthread-2.0", "intl"):
    so_path = os.path.join(glib_lib, "lib%s.so" % name)
    if os.path.isfile(so_path):          # isfile 守卫：无共享版的环境退回裸名搜索
        explicit_inputs.append(so_path)
closure = " ".join(explicit_inputs + ["-L%s" % d for d in lib_dirs])
# 注入生成的 gtk+-3.0.pc 的 Libs: 行首位——pkg-config 展开时顶层模块 Libs 最先输出，
# 故这些绝对路径先于一切 -l 裸名进入链接行
pc_text = pc_text.replace("Libs:", "Libs: %s " % closure, 1)
```

要点：① isfile 守卫（跨 worker 可移植）；② 绝对路径输入先于一切 -L/-l；
③ 同时保留全部依赖 libdir 的 -L/-Wl,-rpath-link 显式闭包（显式 .so 的 DT_NEEDED
链要在这些目录里解析 libffi 等自身依赖）；④ 内嵌注释记录 round-02 finding，
防止后人"优化"回 -L 顺序方案。

## 验证

自包含探针（设备新 shell 可跑通，不依赖本 run 日志）：

```sh
# ① 烘焙实证：首位 -L 是系统前缀目录
P=$(ls -d /storage/Users/currentUser/.conan2/p/ocaml*/p | head -1)
W=/storage/Users/currentUser/tmp/oh-device-porting-v2/lkprobe.$$
mkdir -p $W && cd $W && printf 'let () = print_endline "probe"\n' > lk.ml
OCAMLLIB=$P/lib/ocaml $P/bin/ocamlopt -verbose -o lk.exe lk.ml 2>&1 | grep -oE '\-L[^ ]+' | head -2
# → -L/storage/Users/currentUser/usr/local/lib   （先于 stdlib -L）

# ② 影子形态：首位目录仅 .a；真 .so 在更靠后的 conan 包目录
ls /storage/Users/currentUser/usr/local/lib/ | grep -E '^lib(glib|gobject|gio|gmodule|gthread|intl)'
# → 6 个 .a（libglib/gobject/gio/gmodule/gthread-2.0.a、libintl.a），无同名 .so
for d in /storage/Users/currentUser/.conan2/p/glib*/p; do
  [ -f "$d/lib/libgobject-2.0.so" ] && echo "$d/lib/libgobject-2.0.so"; done
# → conan glib 包内存在 libgobject-2.0.so（被影子化的共享库确实存在）

# ③ lld 目录内选择语义最小对照（与 OCaml 解耦，clang+llvm-ar 自包含）
W2=$W/lld && mkdir -p $W2/sys $W2/real && cd $W2
printf 'extern int dep_of_static(void); int from_static(void){return dep_of_static();}\n' > s.c
clang -c s.c -o s.o && llvm-ar rcs sys/libmine.a s.o      # “系统 .a”：有主符号、缺依赖
printf 'int from_static(void){return 7;}\n' > r.c
clang -shared -fPIC r.c -o real/libmine.so                 # “conan .so”：主符号共享版
printf 'int dep_of_static(void){return 9;}\n' > d.c
clang -shared -fPIC d.c -o real/libdep.so                  # 依赖供给者（对应 libffi 角色）
printf 'int from_static(void); int main(void){return from_static();}\n' > m.c
clang m.c -L$PWD/sys -L$PWD/real -lmine -o t1 2>&1 | grep -m1 'undefined symbol'
# → undefined symbol: dep_of_static ... in archive sys/libmine.a  （r2 同构失败形态）
clang m.c $PWD/real/libmine.so $PWD/real/libdep.so -L$PWD/sys -o t2 && ./t2; echo rc=$?
# → rc=0 （显式 .so 绝对路径输入：一步到位）
```

端到端：round-04 权威 CI（同配方 + 显式 .so 闭包）PASS，T2 无显示器探针真机运行
通过（Glib UTF-8 闭环），T3 消费者编译链接通过。

## 边界

- 适用：ocamlopt（或任何把固定 -L 烘焙进链接行的编译驱动器）× lld 单目录
  .so→.a 选择语义 × 早段搜索目录存有同名静态归档的一切链接场景；与语言无关。
- 反例：首位目录若同时存在同名 .so，lld 目录内本就先 .so，裸名搜索即可；
  显式闭包仍建议保留（implement-policy §5 预防性显式化），但不是本条的"救火"场景。
- 前置检查：先 `ocamlopt -verbose` 确认首位 -L 与该目录 .a/.so 形态，再决定
  显式名单；勿盲目列举不存在的 .so（isfile 守卫兜底，但名单应诚实）。
- 相邻机理（不同层）：Libtool .la 元数据优先级（E236）与 g_libintl_* intl-wrapper
  语义（E508）都会在 glib 静态链场景出现，注意与本条（驱动器 -L × lld 目录语义）
  区分——三者的修复互不替代。

## 查重

检索面：本 run worktree `knowledge/`（graph 544 文件 + drafts；index.tsv 766 行）。
检索词与命中逐项（ffi/pcre2 词面命中全部如实列出）：

| 检索词 | 命中 | 判定 |
|---|---|---|
| `ocamlopt` | E253、E387、index.tsv、DRAFT-9685-bsc-ghc、DRAFT-libnbd-1.9.6-ocaml-bytecode-cache-shebang、ocaml-downstream-bytecode-shebang-stublibs.kv | E253 覆盖 OCaml 工具链迁移四类问题（hmmac/ln -sf/configure/posix_spawn），无链接行 -L/lld 语义（`graph/E253.kv:12,:26`）；其余为 llvm lit / ghc / 字节码 shebang 主题。均非实质 |
| `ffi_type_void\|pcre2_\|libgobject-2\.0\.a` | graph/E236.kv、knowledge/graph/index.tsv、doc/E236.md、DRAFT-stdformat | **词面命中如实列出**：index.tsv 与 doc/E236.md 为 E236 的索引行/doc 孪生；DRAFT-stdformat 的 pcre2 仅是 fmt 链序上下文的偶发词面（:45-46,:130），非同机理。E236 本体 root_cause 为 **Libtool .la 元数据优先级 + llvm-ar 嵌套归档**（`graph/E236.kv`），与本条（驱动器烘焙 -L 首位 × lld 单目录 .so→.a 选择）不同层——列最近邻/相邻条目 |
| `link.order\|链接顺序\|搜索顺序\|-L.*首位` | E028/E280/E294 及数个 draft | 标题核对为 Tcl 线程/共享包测试/lex 等无关主题，0 实质命中 |
| `显式闭包\|explicit.*closure\|绝对路径.*链接` | E423/E296/E517/E537 | 分别为交叉 binutils 验证/Meson cross file/签名 dlopen 拒绝/DT_NEEDED 泄漏——E537（DT_NEEDED 泄漏）为相邻条目，其余非实质 |
| `g_libintl_` | E508（intl-wrapper 语义） | 相邻条目：glib 静态 vendor intl 的一个侧面，无 ocamlopt/lld 语义 |

**经验仓先例披露**（自用检索库，不构成申报查重面，如实引用）：ophs_ci_review main
`link-error/libido3-13.10.0-libintl-link-closure.md`（提交 3fa0bff，2026-09-27）已沉淀
「generate() 把 `dep.package_folder/lib/libintl.so` 以绝对路径追加进链接输入」的修法
范式（libido3 案例，g_libintl_* 症状面）。本条相对它的**新增机理层**：
ocamlopt 固定 -L 首位 + lld 单目录 .so→.a 解析语义、"-L 顺序修复不够"的反直觉发现、
ffi_*/pcre2_* 失败签名——官方面与经验仓此前均未覆盖；libido3+lablgtk3 双实例同时
佐证 L1 复发面。**本条为该修法范式在 OCaml 原生链接场景的机理化与推广，非重复申报。**

同 stem 草稿：DRAFT-ocamlopt-lld-static-shadow-explicit-closure.kv
