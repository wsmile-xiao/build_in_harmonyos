# E429 — 非 worker OHOS 环境上 OCaml 原生链接工具链闭包

> 适配案例：menhir 20260209（PR #14711）。机理为 ocamlopt + Conan registry ocaml 包 +
> OHOS 设备环境语义，不限于该库；适用一切以 `tool_requires("ocaml/...")` 做原生链接的包。

## 1. 背景与症状

制品仓 `ocaml/4.14.1.1.x` 由 CI worker 构建并发布；在缺少 worker 工具链
（`/data/service/hnp`）的 OHOS 设备（如共享开发机）上，用该工具链构建原生 OCaml
包时依次遇到三类失败：

1. **缺 GNU as（汇编阶段）**
   ```
   sh: as: inaccessible or not found
   Error: I/O error: as  -o 'base/.base.objs/native/base.o' '.../camlasm5bd5f9.s'
   ```
   OHOS SDK 只带 LLVM clang（集成汇编器），镜像没有 GNU binutils 的 `as`；ocamlopt
   把 aarch64 汇编交给裸命令 `as`。

2. **烘焙的 worker 编译器路径（链接阶段）**
   ```
   Error: I/O error: /data/service/hnp/bin/clang -O2 ... -o 't.exe' ...
   ```
   `ocamlopt -config` 显示 `c_compiler: /data/service/hnp/bin/clang`（构建时烘焙），
   设备上该路径不存在。

3. **`-cc`/`OCAMLPARAM` 覆盖丢链接参数**
   以 `-cc <cmd>`（或 `OCAMLPARAM=_,cc=<cmd>`）绕过 (2) 后，共享链接失败：
   ```
   ld.lld: error: undefined symbol: main
   >>> referenced by crt1.c:18 ... Scrt1.o:(_start_c)
   ```
   `.cmxs` 链接被当成可执行链接（丢 `-shared`，拉入 Scrt1.o）；可执行链接同时丢
   `-Wl,-E`（宿主不再导出 OCaml 运行时符号，运行时加载 `.cmxs` 插件时 `caml_*`
   解析失败）。根因：覆盖 `cc` 会整体替换 `Config.native_c_compiler` 字符串，驱动
   追加的链接参数随之中断。用包装脚本记录参数可复现该行为：
   `ccwrap -o w.cmxs -L<ocaml_lib> w.cmxs.startup.o a.o`（无 `-shared`）。

## 2. 诊断命令（设备侧，只读）

```sh
P=<ocaml_pkg>
$P/bin/ocamlopt -config | grep -E "c_compiler|native_c_compiler|asm"
command -v as || echo "as missing"
# 复现 2)：baked clang 路径不存在
OCAMLLIB=$P/lib/ocaml $P/bin/ocamlopt t.ml -o t.exe
# 复现 3)：-cc 覆盖后 cmxs 丢 -shared
OCAMLPARAM='_,cc=clang' $P/bin/ocamlopt -shared a.cmx -o a.cmxs
```

## 3. 修复（设备侧工装闭包，三步）

```sh
# (a) as shim：clang 集成汇编器替代 GNU as
printf '#!/bin/sh\nexec "${CC:-clang}" -c "$@"\n' > ~/local/bin/as
chmod +x ~/local/bin/as

# (b) ccwrap：恢复 -cc 覆盖时驱动丢失的链接参数
#     -c 编译透传；*.cmxs/.so 输出补 -shared；可执行链接补 -Wl,-E
#     （要点：检测输出后缀，见 kv 的 rec_command）

# (c) profile 注入（[buildenv] 覆盖构建；[runenv] 覆盖 conan test 的 test() 环境）
#     ~/.conan2/profiles/ohos-aarch64{, -device}:
#       [buildenv] OCAMLPARAM=_,cc=<shim_dir>/ccwrap
#       [runenv]   OCAMLPARAM=_,cc=<shim_dir>/ccwrap
#       PATH=+(path)/<shim_dir>
```

配套（配方侧，与本条互补，见既有知识 `E253` 与
`DRAFT-ocaml-downstream-bytecode-shebang-stublibs`）：
- 构建前导出 `OCAMLLIB=<ocaml_prefix>/lib/ocaml`；
- dune 安装树是符号链接，`package()` 须跟随链接复制真实文件；
- test_package 用绝对路径 + 显式解释器调用（OHOS 拒绝 shebang 直执行）。

## 4. 验证证据（menhir 20260209，2026-10-04 实测）

| 阶段 | 结果 |
|------|------|
| 修复前 | `conan create` 在汇编阶段失败：`sh: as: inaccessible or not found` ×N |
| 加 as shim 后 | 汇编通过；链接失败：`Error: I/O error: /data/service/hnp/bin/clang ...` |
| 加 `OCAMLPARAM=_,cc=clang` 后 | 共享链接失败：`ld.lld: undefined symbol: main`（Scrt1.o） |
| 加 ccwrap 后 | `conan-verify` G0–G4 全 PASS；本地 CI L0/L1/L1e/L2/L4/L5 全 pass；test_package 13/13（code/table 后端生成、ocamlopt 编译链接、运行 7/42、两条负向） |

复现/修复探针：设备 scratch 中 `cmxs`/`exe`/`cmxa→cmxs` 三种链接形态均 rc=0 且可运行。

## 5. 与现有条目的关系（查重边界）

- `E253`（OCaml 工具链迁移）：覆盖 **OCaml 自身**在 OHOS 的 configure/testsuite/平台限制；
  本条覆盖 **下游包消费该工具链做原生链接** 的三个环境缺口，对象不同。
- `DRAFT-ocaml-downstream-bytecode-shebang-stublibs`：覆盖 **字节码**工具 shebang/OCAMLLIB/
  stublibs；本条覆盖 **原生（ocamlopt）链接**的汇编器与链接器程序路径/参数语义，互补不重叠。
- `DRAFT-ocamlopt-lld-static-shadow-explicit-closure`：覆盖烘焙 **首位 -L** 导致的静态归档
  影子化；本条覆盖烘焙 **编译器程序路径** 与 `-cc` 覆盖丢参，机制不同。

## 6. 适用范围与边界

- 适用：无 `/data/service/hnp` worker 工具链、无 GNU `as` 的 OHOS 设备上的本地/真机门禁；
  跨库适用（dune/findlib/cairo2/zarith/lablgtk3/menhir/xmlm 等所有原生 OCaml 包）。
- 不适用：平台 CI worker（具备完整 worker 工具链，归档原样构建即通过）——本条不改变归档。
- 反例/禁止：修改共享 conan cache 或对已发布包做二进制打补丁（不可复现、污染全局）；
  把 `/data/service/hnp` 路径写进配方/补丁（R33/R39）；用
  `-Wl,--allow-shlib-undefined` 掩盖丢参（产物运行期崩）。
- 解除条件：若 registry 的 ocaml 包改为按运行时环境解析 C 编译器路径（或 OHOS 镜像补齐
  GNU binutils），本条降级为历史诊断参考。

## 关联条目

- 相关：E253、DRAFT-ocaml-downstream-bytecode-shebang-stublibs、
  DRAFT-ocamlopt-lld-static-shadow-explicit-closure
