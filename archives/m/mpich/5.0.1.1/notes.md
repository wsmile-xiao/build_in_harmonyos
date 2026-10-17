# mpich 5.0.1.1 适配笔记

## 版本说明（重要）

上游 pmodels/mpich **只有 v5.0.1 这一个 tag**，不存在 5.0.1.1。
`5.0.1.1` 是本仓库的**适配修订版号**：源码直接取官方 `mpich-5.0.1.tar.gz`
（sha256 `8c1832a13ddacf071685069f5fadfd1f2877a29e1a628652892c65211b1f3327`，
与 conandata.yml 一致），末尾 `.1` 表示 HarmonyOS 适配修订，同时满足 R37
「四段版本号」规则，保证修复后的配方能以新版本号发布到 cnb.cool 制品仓。

## 编译环境

- 构建系统: autotools（configure + make，out-of-source 于 conan build 目录）
- 编译日期: 2026-08-15（本轮复验，含 conan create 复现 + 上游 test/mpi 实跑）
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，`/data/service/hnp/bin/clang`）
- 链接器: ld.lld / llvm-ar / llvm-ranlib / llvm-nm
- 目标平台: HarmonyOS aarch64（musl），HongMeng Kernel 1.12.0
- 状态: published（conan create 复现通过 + test_package 真机冒烟通过 + 上游测试 100% 通过）

## configure 命令

配方实际执行（`conanfile.py::build`，含构建期修复后的完整参数）：

```bash
SHELL=/data/service/hnp/bin/bash CONFIG_SHELL=/data/service/hnp/bin/bash \
CC='bash /data/service/hnp/bin/clang' CXX='bash /data/service/hnp/bin/clang++' \
AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib \
NM=/data/service/hnp/bin/llvm-nm LD='bash /data/service/hnp/bin/ld.lld' \
bash <source>/configure \
  --prefix=/ --disable-fortran --disable-cxx --disable-romio \
  --with-device=ch3:sock --with-pm=gforker --with-pmi=pmi1 \
  --with-pmilib=install --with-hwloc=no --with-wrapper-dl-type=none \
  --with-datatype-engine=dataloop --enable-fast=all --enable-g=none \
  --enable-shared --disable-static --build=aarch64-unknown-linux-gnu \
  CONFIG_SHELL=/data/service/hnp/bin/bash
make -j1 SHELL=/data/service/hnp/bin/bash ... CC/CXX/AR/RANLIB/NM/LD
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 执行到 `confOLACAJ/subs1.awk: Permission denied`（MPL 子 configure 失败） | HarmonyOS `/tmp` 是只读 erofs；autoconf 在 TMPDIR 下用 `umask 077 && mktemp -d` 建的 0700 临时目录在本平台**即使属主也不可写**，awk 脚本复制进目录后无法读取/执行 | 构建期把源码树所有 configure/子 configure 脚本里的 `umask 077` 替换为 `umask 002`（生成 2771 组可写目录），并把 TMPDIR/TMPPREFIX 指向 conan build 目录；测试期对 config.guess 同样处理 |
| 2 | `/bin/bash: bad interpreter` / `#! /bin/bash` 脚本无法运行 | HarmonyOS 无 `/bin/bash`，bash 在 `/data/service/hnp/bin/bash` | 构建/测试期把脚本 shebang 改写成真实 bash 路径 |
| 3 | config.guess: unable to guess system type | config.guess 不认识 HarmonyOS | 显式传 `--build=aarch64-unknown-linux-gnu`（主 configure 与 test/mpi 子 configure 均需） |
| 4 | mpicc wrapper 打包后路径错误（`prefix=/` 写死） | configure 用 `--prefix=/`，wrapper 生成的 `-I//include -L//lib` 在目标机上无效 | 打包期按 `bin/../` 相对路径重写 wrapper 的 prefix/exec_prefix/sysconfdir/includedir/libdir |
| 5 | 运行报 `Error loading shared library libmpi.so.12` | 共享库构建，运行期找不到动态库 | 运行测试/冒烟前 export `LD_LIBRARY_PATH=<package>/lib` |
| 6 | 老式 mpiexec 不支持 `--version`/`MPIEXEC_TIMEOUT` | `--with-pm=gforker` 配套的是经典 mpiexec（无 --version；MPIEXEC_TIMEOUT 是 hydra 专用） | 测试脚本用外部 `timeout` 兜底；test_package 冒烟用 `mpiexec -n 2` |

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| perl | 5.42.2 | tool_require（configure 生成 Makefile 需要） |
| clang/clang++ | OHOS SDK 26.0.0.18 (llvm 15) | 编译工具链 |
| bash | bash 5.3 (`/data/service/hnp/bin/bash`) | CONFIG_SHELL |

> mpich 为无第三方运行时依赖的独立库（已 --with-hwloc=no，禁用 hwloc/json-c 外部依赖）。

## 验证结果

1. **conan create 复现（W3 门禁，2026-08-15）**：`conan create archives/m/mpich/5.0.1.1 -o mpich/*:shared=True`
   （profile `ci/conan/profiles/ohos-aarch64`，host/build 同 profile）通过，
   产出 `mpich/5.0.1.1#9c922d10c88252fd894a5f836aacfe30`
   （package `01d92cf349a0dd98ff915f4bd99a04430171517f#648de0c040713cb2544bcc85e6ea32c4`，
   logs: `reports/conan-create-20260815.log`）。
2. **test_package 真机冒烟**：`mpiexec -n 2 ./test_mpi` 通过，
   校验 MPI_Comm_rank/size、MPI_Allreduce 求和、MPI 库版本字符串均正确（2 ranks）。
3. **上游 test/mpi 测试（2026-08-15 实跑）**：将 test/mpi 源码以
   `./configure --with-mpi=<package> --build=aarch64-unknown-linux-gnu` 重新配置并
   `make` 重建 basic/comm/coll/pt2pt 四个目录，再用打包的 `mpiexec` + 外部
   `timeout` 逐条运行（经典 mpiexec 无 MPIEXEC_TIMEOUT）。结果见
   `reports/upstream-tests-20260815.log`：

   | 目录 | 执行 | 通过 | 跳过 |
   |------|------|------|------|
   | basic | 8 | 8 | 0 |
   | comm  | 46 | 46 | 0 |
   | coll  | 208 | 208 | 5 |
   | pt2pt | 83 | 83 | 6 |
   | **合计** | **345** | **345** | **11** |

   **通过率 345/345 = 100%**（0 失败）。
   11 个跳过用例均为上游标记/内存约束，非本平台缺陷：
   - `coll/gather_big`(mem=20.1GB)、`coll/coll_large`(mem=80/100GB)：testlist
     声明内存远超本设备可用预算（~11GB MemAvailable），跳过避免 OOM；
   - `pt2pt/issendselfcancel`、`scancel`、`scancel2`、`pscancel`、`cancelrecv`、
     `scancel_unmatch`：上游 testlist 标记 `xfail=ticket2266/ticket2276`
     （上游已知失败），按上游 runtests 惯例（默认跳过 xfail）处理。

## 注意事项

- 运行任何 MPI 程序必须先设置 `TMPDIR`（可写目录）与 `LD_LIBRARY_PATH`（含 `<pkg>/lib`），
  否则 /tmp 只读与动态库加载会报错。
- `basic/self` 等自通信用例只能以 1 个进程运行；多进程下 ch3:sock 的 eager-connect
  会对已退出的对端报 Connection refused（属测试用法问题，非库缺陷）。
- GPU/HIP（`*_gpu`/`*_hip`）与 Fortran/C++ 绑定（--disable-*）对应用例不在本包范围内。
- 该包只含 C 绑定（`--disable-cxx --disable-fortran`），需要 C++/Fortran MPI 绑定请另行适配。
