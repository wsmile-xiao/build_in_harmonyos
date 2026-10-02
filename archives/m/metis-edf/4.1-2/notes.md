# metis-edf 4.1-2 适配笔记

## 上游与版本坐标

- 上游：METIS 4.0.1 的 EDF/Code_Aster 变体，落包为 `metis-edf_4.1-2.orig.tar.gz`。
- 官方只提供 `http://www.code-aster.org` 与 `http://www-users.cs.umn.edu/~karypis/metis`（均为
  明文 http，且已失效），因此按本队惯例取 **Ubuntu multiverse 的 orig tarball（HTTPS）**：
  `https://archive.ubuntu.com/ubuntu/pool/multiverse/m/metis-edf/metis-edf_4.1-2.orig.tar.gz`
  sha256 `e8377a7d9f56af8cb04dcab5c8c383d201f1c234197b059894567896da478c28`
  （与 `metis-edf_4.1-2-4build2.dsc` 的 `Checksums-Sha256` 逐字符一致）。
- 解包根目录 `metis-edf-4.1/`。

## 为什么走 clang 直编

`Makefile` → `CONFIG/configure` 只认 SunOS/OSF1/IRIX64/Linux/Cygwin，并且硬编码
gcc/g77/gfortran、直接用 `uname` 判定平台。绕过整个 `configure`，用 OHOS clang 直接编译
（同 sxid / libblocksupport / isight-firmware-tools 的做法）：

- `Lib/*.c`（52 个）→ `libmetis.a`；
- `Programs/{pmetis,kmetis}.c` + `io.c` → `pmetis` / `kmetis`；
- `Programs/onmetis.c` + `io_aster.c` + `smbfactor.c` + Fortran 移植 → `onmetis`。

编译标志：`-O2 -fcommon -std=gnu17 -Wno-implicit-function-declaration -Wno-implicit-int`。
`-fcommon` 用于 1998 年代 C 的 tentative definition；`GKfree` 的声明在 `proto.h` 里被注释
掉了（`/*void GKfree(void **,...); */`），故必须降级隐式函数声明。

## Fortran 移植（本库的关键点）

上游只有 `onmetis` 需要 Fortran：`Programs/Makefile` 的 `ONMETISOBJS` 含
`ecri11.o lect11.o lect00.o`（`lect10.f` 未参与链接）。OHOS 工具链没有 Fortran 编译器，
conan 制品仓也没有 gfortran/flang，所以这三支例程按 ISO C **等价移植**为
`port_fortran_io.c`（放在配方根，`source()` 时复制进 `Programs/`，原 `.f` 文件保持原样）：

- `lect00_`：读 `fort.81` 的 `n ll`；
- `lect11_`：读 `n ll niv ifm` + `xadj(n+1)` + 每行邻接，再整体减 1（0 基）。
  注意：文件里的 `ll` 读进**局部变量**（Fortran 里 `ll` 是局部），dummy 参数 `long`
  仍是调用方传入的 `2*nedges`，用它驱动 adjncy 的重编号循环。
- `ecri11_`：按 `FORMAT(I10,E20.6,2I10)` 写头 + `(8I10)` 写 `invp/perm/supnd/parent`，
  自制 Fortran `E20.6` 字段（`0.ddddddE±ee` 右对齐 20 列）。

移植正确性用上游自带的 `Test/fort.81` 验证：

- 解析出的图 = `14944` 顶点 / `86601` 边，与 `fort.81` 头一致；
- 生成的 `fort.85` `invp` 列 = `fort.81.iperm + 1`，`fort.85` 整数总数 = `2n+2*nbsn+1`，
  `iperm` 是 `0..n-1` 的排列。
- **附带发现**：随包的 `Test/*.ref` 与任何现代 libc 构建都**不一致**（本机 Windows + glibc
  兼容 RNG、WSL Ubuntu glibc 均得到 `nbsn=6818`，`.ref` 是 `6828`）。原因是 METIS 4.x 的
  `RandomInRange` 用 `drand48()`、`RandomPermute` 用 `rand()`，排序结果依赖生成 `.ref`
  时的 libc。上游 `Test/Makefile` 本身**不做比较**（README 只是让人肉对照），所以本配方
  实跑两个 target 并做**结构校验**，不宣称与 `.ref` 字节一致。

## 产物

- `lib/libmetis.a`
- `include/{metis.h,defs.h,struct.h,macros.h,rename.h,proto.h}`（`metis.h` 会
  `#include` 其余 5 个头，需一并安装）
- `bin/{onmetis,pmetis,kmetis}`

## 平台实测

- 真机 `conan create`（`ohos-aarch64`）：`CREATE_RC=0`。
- 上游 `Test/fort.85`、`Test/vers_check` 两个 target 等价命令实跑通过：
  `onmetis fort.81` 退出码 0、`onmetis --version` 输出 `metis-edf-4.1`。
- 消费者：`test_metis_edf.c` 10 项 + `onmetis --version` / `pmetis` / `kmetis` 3 项 = 13/13。
