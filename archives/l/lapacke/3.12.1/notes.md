# lapacke 3.12.1 编译笔记（HarmonyOS PC · netlib lapack 源树 · 纯 C 独立 LAPACKE）

## 定位与交付形态
- LAPACKE 是 LAPACK 的标准 C 接口。本包 `lapacke/3.12.1` 以 **netlib lapack
  3.12.1 源码树** 交付独立 C 接口库：requires `lapack/3.12.1`（同一官方 tarball、
  同一版本口径，sha256 `2ca6407a…` 与 lapack/3.12.1 conandata 一致）。
- 与 `liblapacke/0.3.30`（OpenBLAS 内嵌 LAPACKE，符号在 libopenblas 内）互补：
  两个任务分属 reference-LAPACK 与 OpenBLAS 两个生态，消费者按引擎选择。
- 交付物：`include/`（lapacke.h、lapack.h、lapacke_64.h、lapacke_config.h、
  lapacke_utils.h + 生成的 lapacke_mangling.h）+ `lib/liblapacke.a`（纯静态，
  package_type=static-library）。

## 路线决策
- **采用：独立纯 C 编译**。只编译 `LAPACKE/src`（2522 个 .c）+ `LAPACKE/utils`
  （156 个 .c），共 2678 个翻译单元；Fortran 本体（liblapack/libblas）与 flang
  运行时（libFortranRuntime/libFortranDecimal）由依赖 lapack/3.12.1 包静态闭合。
- **弃：上游 CMake BUILD_LAPACKE=ON**——该入口触发 FortranCInterface_VERIFY
  链接验证，flang-ohos 精简运行集无法完成（lapack/3.12.1 先例的 package_info
  注释明确其 CBLAS/LAPACKE 因此未构建）。CMake 路线在本平台产不出 lapacke。
- **弃：shared 选项**——实测（本任务 probe 环节）LAPACKE 包装层引用的
  `cgbrfsx_/cgesvxx_/dgeqpf_/clatms_` 等约 21+ 个 extras 符号在 reference
  liblapack.a 中不存在（上游默认构建面不含 XX 精化族与 matgen 辅助族）：
  - 静态 .a：链接器按需拉取对象，未引用的缺口例程不参与链接 → 主流 API 完整可用；
  - 自包含 .so：全部对象必须进 .so，其未定义符号被消费者 lld
    `--no-allow-shlib-undefined` 拒绝 → 本平台不可交付。
  该缺口与上游参考实现自身一致（netlib 共享 lapacke 同样依赖其共享 lapack
  提供 extras），非适配引入。

## 关键构建细节
- **lapacke_mangling.h 生成**：复制 `include/lapacke_mangling_with_flags.h.in`
  为 `lapacke_mangling.h`。实测 3.12.1 tarball 的该模板不含占位符，默认分支
  即命名修饰 `lcname##_`（ADD_），与无后缀 reference LAPACK 的 Fortran 符号
  （`dgesv_` 等）一致。
- **编译**：设备 hnp clang（profile `tools.build:compiler_executables` c 项，
  兜底 `/data/service/hnp/bin/clang`），`-O2 -fPIC -I LAPACKE/include`；
  设备 xargs 为 busybox 形态（无 `-I{}`），用 `ls *.c | xargs -P <jobs> -n 16
  <cc> ... -c` 批量追加形式（clang 多 -c 输入，对象落各自源码目录）。jobs 上限 4。
- **归档**：hnp llvm-ar `rcs`（兜底 ar），对象数断言 == 2678（2522+156 实数）。
- **链接闭合顺序**（demo/test 同款）：`liblapacke.a → -llapack → -lblas →
  -lFortranRuntime → -lFortranDecimal → -lm`（依赖包 lib/ 实际交付的四件 + m）。
- **头文件集**：lapacke.h `#include "lapack.h"` 与 `"lapacke_64.h"`，六件一起
  交付；缺 lapack.h 时消费者连 `#include <lapacke.h>` 都编不过。

## 上游测试（R51 三步）
1. **清点**：LAPACKE 域可执行测试资产 = `LAPACKE/example/Makefile` `all` 目标
   4 个演示程序（DGESV/DGELS × colmajor/rowmajor，N=4）。example/ 另有 *_64
   变体 4 个（ILP64 口径，属 lapacke64 任务域）与 example_user.c（文档示例，
   不在 all 目标），均不在本包范围；上游 Fortran 套（TESTING/）属 lapack/
   blas 本体验证域，不在 LAPACKE C 接口层。
2. **实际运行**：build() 内编译链接本构建产物并在设备真实执行（上游入口
   `$(FC)` 链接 + `./$@` 就地执行；此处仅链接器换成设备 CC，同 liblapacke
   0.3.30 先例的轻量默认路径，编译对象/头文件/被链库保持上游语义）。
3. **回填**：4/4 全部 PASS（0 SKIP），stdout 于 conan create 构建日志；
   test_package 另有 8 项断言（见 test_package/MANIFEST.yml）。

## 上游已知问题（不修改上游源码）
- `lapacke_example_aux.c:63` LAPACK_IFMT 格式告警（int64_t vs int）：上游自身
  格式串问题，输出数值正确，保持上游原样。
- **v3.12.1 tag 版本字符串未随发布更新**：官方 tarball（sha256 `2ca6407a…`，
  即 lapack/3.12.1 conandata 登记的同一官方资产）内 `INSTALL/ilaver.f` 与
  `CMakeLists.txt` 均为 3.12.0，`LAPACKE_ilaver` 实测返回 (3,12,0)。test.c
  的版本断言按源码树真实行为锚定为 3.12.0，注明缘由。

## 验证记录（候选提交前 probe）
- 源码 sha256 实测一致（gh-proxy 镜像下载件与官方 sha256 校验一致，conandata
  仅登记官方源 URL）。
- 2678 对象编译 0 错误；liblapacke.a 归档 2678 成员。
- 4 个 demo 静态链接 + 设备实跑全过（解向量/LU 分解数值正确）。
- test_package/test.c 8 项断言在设备实跑全过（提交前复验记录见 logs）。
