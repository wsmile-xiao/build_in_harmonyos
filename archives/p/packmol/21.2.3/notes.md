# Packmol 21.2.3 适配笔记（HarmonyOS PC, os=OHOS arch=armv8）

## 上游契约

- 纯 Fortran：`src/` 38 个 `.f90`（自由格式）+ 1 个 `gencan.f`（F77 固定格式）+ `app/packmol.f90` 主程序。
- 构建系统：手写 `configure`（bash，仅探测 Fortran 编译器并改写 Makefile `FORTRAN=` 行）+ `Makefile`
  （`FORTRAN`/`FLAGS` 变量，默认 `FLAGS=-O3 -march=native -funroll-loops`，**无 install 目标**）。
  备选 `CMakeLists.txt`（有 install）与 `fpm.toml`，本配方走 Makefile 路线。
- 源码源：官方 `https://github.com/m3g/packmol/archive/refs/tags/v21.2.3.tar.gz`，
  sha256 `b26af58d407b1c8d786aa6c2bb6bfa40d741aaa0424db51300fdd6fd66dd4813`（实测）。
- 依赖：无外部库（内嵌 GENCAN 优化器；无 BLAS/LAPACK/MPI/OpenMP 调用，R 语言依赖仅上游文档提及）。

## OHOS 适配方案（根因驱动）

1. **Fortran 编译器**：设备/NDK 无 Fortran 编译器，`tool_requires("flang-ohos/20.1.0")` 提供 LLVM Flang
   前端；`FORTRAN=<flang-ohos bin>/flang` 传入 Makefile。flang 按扩展名自动选自由/固定格式，
   F77 的 `gencan.f` 实测直接编译通过。
2. **最终链接（关键）**：flang-ohos 是前端工具包，**不含 OHOS CRT / sysroot / libc / libunwind /
   compiler-rt**（直接让 flang 链接报 `Scrt1.o/crti.o/-lm` 缺失）。因此：
   - 补丁 `0001-linker-variable.patch` 把 Makefile 最终链接行从 `$(FORTRAN) ... $(FLAGS)`
     分离为 `$(LINKER) ... $(FLAGS) $(LIBS)`，并在文件头新增 `LINKER ?= $(FORTRAN)`/`LIBS ?=`
     保持上游默认语义不变（`make LINKER=...` 仅被覆盖时生效）。
   - 配方注入 `LINKER=<OHOS clang>`（profile conf 的 `tools.build:compiler_executables`）
     与 `LIBS="-L<flang lib> -lFortranRuntime -lFortranDecimal -lm"`。
   - 该方案与 `fortran-shlex/2.0.1`、`scalapack/2.2.3`（flang-ohos 的既有消费者）一致。
3. **flags 可复现性**：上游默认 `-march=native` 在受控 CI 不可复现，配方固定
   `FLAGS="-O3 -funroll-loops -march=armv8-a"`（与 profile arch=armv8 一致）。
4. **打包**：Makefile 无 install 目标，`package()` 直接把构建产物 `packmol` 复制到 `bin/`，
   LICENSE 复制到 `licenses/`。
5. **签名**：本机实测未签名 ELF 可直接运行（banner + 真实打包均成功）；若目标镜像要求
   E077 签名，由发布流水线 `ci/artifacts/sign.sh` 在 upload 阶段处理，配方不内置平台特定签名。
6. **运行模型**：packmol 从 stdin 读输入、输出写当前工作目录，天然适配非交互环境；
   `seed -1` 表示按时间取种（不可复现），测试必须固定 seed（上游 test_cli.sh 自动替换为 1024）。

## 补丁清单

| 补丁 | 变更 | 理由 |
|---|---|---|
| `0001-linker-variable.patch` | Makefile：新增 `LINKER ?= $(FORTRAN)`/`LIBS ?=`，链接行改用 `$(LINKER) ... $(FLAGS) $(LIBS)` | flang-ohos 无 CRT/sysroot，链接必须交由平台 clang 驱动；默认值保持上游语义 |

## 测试记录（R51 申报）

上游测试清点（`testing/`）：
| 测试 | 内容 | HarmonyOS 实测 |
|---|---|---|
| `test.sh` / `runtests.jl` | Julia 驱动 17 个输入文件回归 + 失败/连接性/CLI 测试 | ❌ 未运行：CI 无 Julia 工具链（本项目能力矩阵未含 julia）；脚本会先 `which julia` 失败。非静默跳过——此受限原因 |
| `test_connectivity.sh` | benzene2/water_box 的 CONECT 输出一致性 | ✅ 通过（1/1） |
| `test_failed.sh` | 预期失败输入须输出指定关键字（FORCED/outside） | ✅ 通过（2/2） |
| `test_cli.sh` | 19 个输入 ×（stdin/-i/-o）3 种调用产出一致 | ✅ 通过（19/19，需 bash+gawk+sed+grep+diff，设备均具备） |

注：`test.sh` 等价于把 runtests.jl（Julia）+ 三个 shell 测试串联；shell 三件已全部实测，
Julia 部分因工具链缺失未运行。

test_package（Conan L1）双消费路径：
1. `run_smoke.sh`（绝对路径调用）：固定 seed 真实打包 20 个水分子，断言
   `water_smoke.pdb` 生成、含 `TITLE Built with Packmol`/`HETATM`、日志含 `Success!`；
2. PATH 消费调用（等价上游 `python/tests/test_packmol.py` 的 subprocess 用例）：
   conanrun 环境把包 bin/ 注入 PATH，以命令名 `packmol < packmol_xyz.inp` 执行
   XYZ 水盒打包，断言 `output.xyz` 生成（设备无 pytest，上游该用例未直接运行）。
两路径均已在 conan create 中实测通过（`SMOKE_OK` + output.xyz 断言）。

## 本地 conan create 验证

```bash
conan create archives/p/packmol/21.2.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -tf test_package
```
- 结果：**通过**（RC=0，`SMOKE_OK` + PATH 消费断言）
- 配方 RREV：`b50ee3f8d6705007498fcfd91ecfa6dd`；包 ID：`6b129b068851896169fae42d399fa922d239ce8a`；
  PREV：`87d5f02bff5f7a3f84165cd0689c6f2f`
- 产物：`bin/packmol`（ELF arm64，动态链接 musl ld）+ `licenses/LICENSE`
- 上游 shell 测试在打补丁后的源码上实测（探针环境），详见 `reports/TEST_REPORT.md`

## 仓库 CI 模拟（build_and_test.sh）

```bash
CI_PACKAGES="archives/p/packmol/21.2.3" zsh ci/conan/build_and_test.sh
```
- 结果：**通过**（CI_RC=0，Total 1 / Success 1 / Pass rate 100%）
- 门禁：L0 pass、L1 pass（含 L1e 破坏性反向证明：移走 bin/ 后测试确实失败）、
  L2 skip（packmol 无 `--version`/`--help`，非阻塞）、L4 pass（补丁扫描）、L5 pass（bin/ 有产物）
- 副作用已清理：ci-metadata.json、conandata.yml.orig、test_package 生成的 env 文件均删除；
  注意 build_and_test.sh 的 pre-download 会把 conandata.yml 改写为 gh-proxy 双 URL 并留存
  `conandata.yml.orig`，跑完需用 .orig 还原为单官方 URL 并删除 .orig（本适配已处理）。
---

**编译结束**: 2026-09-06 11:21
**最终状态**: built
