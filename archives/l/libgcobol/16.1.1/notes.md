# libgcobol 16.1.1 适配笔记（HarmonyOS PC · 真机 shadow CI 已通过）

## 状态：✅ 真机 shadow CI 通过 + 补全 GCOBOL 前端端到端测试（2026-09-23）

- L0_RESULT=pass（质量门禁全过）
- L1_RESULT=pass（test_package 执行，含 L1e 破坏性负测试）
- L2_RESULT=skip（库包无 bin/ 目录，正常）
- L4_RESULT=pass（无补丁）
- L5_RESULT=pass（lib/ 有产物）
- test_package 两层断言全通过：
  - ABI 探针 3 条 —— `__gg__power_of_ten(2)=100, (0)=1, (5)=100000`
  - **GCOBOL 前端编译 + 链接 libgcobol + 运行真实 COBOL 程序 7 条** ——
    `COMPUTE 10**2=100`、`3.5*2=07.00`、`MOVE 字符串`、`IF`、`PERFORM 1..5 求和=015`、
    `FUNCTION MAX=8`、`FUNCTION MIN=-14`
- **libgcobol 源码树内 compat/posix 子库 5 个测试全部通过**（用 GCOBOL 前端编译 + 链接 libgcobol 运行，属 464 项 cobol.dg 之外的子库冒烟验证）：
  - `compat/t/smoke.cbl`：`CBL_ALLOC_MEM/CBL_CHECK_FILE_EXIST/CBL_DELETE_FILE/CBL_FREE_MEM`
    4 个 compat 子库函数真实调用通过（alloc +0、check +1、delete -1、free +0，符合预期）。
  - `posix/t/{errno,exit,localtime,stat}.cbl`：`posix-mkdir/posix-errno/posix-exit/
    posix-localtime/posix-stat` 5 个 posix UDF 真实调用通过（均 exit 0）。
  - 为此修复了 GCOBOL 前端 3 个缺陷（见 feat/gcobol-16.1.0）：`cdf_literalize` 字符串
    CDF 值 initial 为空、`symbol_match`/`symbol_map` 对「用户声明 RETURN-CODE 覆盖预定义
    全局寄存器」的消歧。
- 上游测试：libgcobol 无独立套件，完整 COBOL 语义测试在 GCC 顶层 `gcc/testsuite/cobol.dg`
  （464 项，GCOBOL 前端编译 + libgcobol 运行）；该 464 项已在 feat/gcobol-16.1.0 真机
  **逐项真实编译+链接+运行通过（PASS 450 + XFAIL 13 + FAIL 0 + SKIP 1）**，即 libgcobol
  运行时的完整覆盖证据。

## 一、上游与版本说明（重要）

- 上游：GCC 16 的 COBOL 运行时库，由 COBOLworx `gcc-cobol` 项目贡献并并入 GCC 主树。
  - 主树位置：`gcc.git` 的 `libgcobol/`（https://gcc.gnu.org/git/?p=gcc.git;a=tree;f=libgcobol）
  - 独立开发仓库：https://gitlab.cobolworx.com/COBOLworx/gcc-cobol（`libgcobol/` 子目录）
- 许可证：`GPL-3.0-or-later WITH GCC-exception-3.1`（GCC Runtime Library Exception，分发友好）。
- 性质：libgcobol **不是独立三方库**，而是 GCC 的 target library（与 libgomp/libstdc++ 同级），
  仅被 GCOBOL 前端编译出的 COBOL 可执行文件链接（见 libgcobol/README）。

### 版本号 16.1.1 的澄清

- issue 指定 `libgcobol 16.1.1`，但 **GCC 官方只发布 `.0` 主版本 tarball**：
  `gcc-16.1.0`（2026-04-30）与 `gcc-16.2.0`（2026-08-07）。
- ftp.gnu.org/gnu/gcc/ 目录确认：**不存在 `gcc-16.1.1.tar.xz`**，GCC git 也无 `releases/gcc-16.1.1` tag。
- `16.1.1` 是发行版从 `releases/gcc-16` 分支 git 快照打包的版本号。
- 本配方 Conan 包版本取 issue 的 `16.1.1`，上游源码用最接近的官方发布 `gcc-16.1.0.tar.xz`，
  二者不一致需在 PR 说明中解释。

## 二、W0 依赖结论

| 依赖 | 类别 | 结论 |
|------|------|------|
| libxml2 | 运行时（xmlparse.cc） | ✅ 已满足（ohpcd 制品仓有 `libxml2/2.15.3` 预编译 OHOS 二进制） |
| libquadmath | Float128，可选 | ⚠️ 已 `--disable-libquadmath` 规避 |
| gcobol 前端 | 编译 posix/compat COBOL 子库 | ✅ **release 16.1.0 无需**（见第三节，主库为纯 C++） |
| libgcc / libstdc++ / compiler-rt | 128-bit 运算辅助符号 | ⚠️ 需在链接阶段显式加 `-lclang_rt.builtins` |

- 依赖数量：4；已满足：libxml2；缺失：无（libquadmath 已禁用、gcobol 前端 16.1.0 不需要、
  compiler-rt builtins 由 OHOS clang 资源目录提供）。
- 是否需拆分依赖适配：**否**（release 16.1.0 的 libgcobol 主库为纯 C++，无需 gcobol 前端）。

## 三、W1 源码与构建系统分析（重要修正）

- 构建系统：autotools，发布 tarball 自带现成 configure（无需 autoreconf）。
- **关键修正**：release 16.1.0 的 `Makefile.am` 只有 `toolexeclib_LTLIBRARIES = libgcobol.la`
  （纯 C++，`SOURCES` 全部为 `.cc`），**不含**需要 gcobol 前端的 posix/compat COBOL 子库
  （那是 16.1.0 之后的 HEAD 才加入的）。故 libgcobol 16.1.x 主库**不需要 gcobol 编译器**。
- 源码获取：无独立 tarball，从 `gcc-16.1.0.tar.xz` **选择性解压** `libgcobol/` + `gcc/BASE-VER`
  + 树根 autotools 辅助脚本（install-sh/config.guess/config.sub 等），避免解压整个 2 GB
  GCC 树导致 HMDFS 磁盘耗尽（Errno 28）。
- configure 依赖 `../gcc/BASE-VER`（版本号）与树根 aux 脚本，二者已由选择性解压提供。
- `configure.tgt` 对 `aarch64-*-linux*` 判定 `LIBGCOBOL_SUPPORTED=yes`。

## 四、W2/W3 配方与 test_package

- 配方：`conanfile.py`（autotools），`conandata.yml`（源码 URL + SHA256）。
- 源码：`gcc-16.1.0.tar.xz`，SHA256 `50efb4d94c3397aff3b0d61a5abd748b4dd31d9d3f2ab7be05b171d36a510f79`（实测复核）。
- 依赖声明：`libxml2/2.15.3`。
- test_package 两层：
  - `test.cpp`：libgcobol 无对外头文件，按 ABI 声明 `extern "C" __int128 __gg__power_of_ten(int)`，
    链接 libgcobol.so 做 3 条真实计算断言（`10^2=100`、`10^0=1`、`10^5=100000`）。
  - `test.sh` + `test_program.cob`：用 GCOBOL 前端（`feat/gcobol-16.1.0` 适配产物，真机
    build tree 的 `gcobol` 仅作为**编译器**）编译真实 COBOL 程序、链接「被测包」libgcobol
    （`LIBGCOBOL_LIBDIR` = `conan create` 产出制品的 lib 目录，**非**真机 build tree 的
    `.libs`）、ELF 签名、运行，断言 COMPUTE 整数/浮点、MOVE、IF、PERFORM、FUNCTION MAX/MIN
    共 7 条（共 10 条断言）。
  - 诚实性：GCOBOL 前端不可用时 `test_package/conanfile.py` 如实输出 `[SKIP]`（不伪造通过），
    `test.sh` 被直接调用则退出非零；前端可用时端到端测试**消费被测包**做完整验证。

- 适配源码修改的实现方式：配方在 `build()` 内用 Python 文本替换做源码适配（`configure`
  的 `mktemp -d "./confXXXXXX"` 临时目录、`libgcobol.cc` 的 `_Float32`/`_Float64`），
  未采用 `.patch` 文件形式（HMDFS 上 patch 工具可用性受限、文本替换更稳），故
  `conandata.yml` 的 `patches` 为空是如实声明（无 .patch 文件）。

## 五、真机 shadow CI 适配要点（全部已解决）

真机 IP 10.62.178.77:2222，隔离 job `libgcobol-16.1.1-shadow-20260921-204917`。逐项解决的适配问题：

1. **依赖解析**：shadow 隔离 job 默认只有 conancenter remote，依赖会解析到 conancenter 版
   libxml2（其 cmake build-requirement 不支持 OHOS）。需手动 `conan remote add ohpcd
   https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/` 并 `conan remote disable
   conancenter`，让依赖命中仓库已发布的 `libxml2/2.15.3` 预编译 OHOS 二进制。
2. **选择性解压**：`source()` 用 `download()` + `tarfile` 只提取 `libgcobol/`、`gcc/BASE-VER`、
   树根直接文件，避免解压 2 GB GCC 树耗尽 HMDFS 磁盘。
3. **configure 无执行位**（E046/E087）：HMDFS 解压后 configure 丢失 +x 且 chmod 不生效，用
   `/bin/sh configure` 执行。
4. **install-sh 缺失**：configure 需要树根 aux 脚本，选择性解压需一并提取。
5. **ar/nm/ranlib/ld 缺失**（E012）：OHOS 只有 LLVM 工具链，configure 前 export
   `AR=llvm-ar NM=llvm-nm RANLIB=llvm-ranlib LD=ld.lld` 等（绝对路径）。
6. **config.status 临时目录**（E011/E052/E060）：HMDFS 上 `mktemp -d "./confXXXXXX"` 失败，
   patch configure 为 `mktemp -d "$TMPDIR/confXXXXXX"` 并设 `TMPDIR=/data/storage/el2/base/cache`。
7. **`_Float32`/`_Float64`**（C23 类型）clang++ 不认识，替换为 `float`/`double`。
8. **128-bit 运算符号**（__divti3/__gttf2 等）：OHOS clang 用 compiler-rt，链接阶段显式
   `LIBS='-lclang_rt.builtins'`（注意不能加在 configure 阶段，否则触发 GCC_NO_EXECUTABLES）。
9. **test_package 的 clang++**：test_package 的 self.run 需 `env="conanbuild"` + clang++ 绝对路径。

## 六、真机 shadow CI 命令

```sh
# 连通性
ssh -i C:\Users\ASUS\.ssh\ohos_pc_codex_ed25519 -p 2222 \
  -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes currentUser@10.62.178.77 "echo ok"

# 创建隔离 job
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" --user codex \
  --job libgcobol-16.1.1-<ts> --package archives/l/libgcobol/16.1.1 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"

# 配置依赖源（关键）
cd <job> && . ./env.sh
conan remote add --force ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
conan remote disable conancenter

# 执行 runner
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

## 七、阻塞点与下一步

- 已完成：W0/W1 分析、配方、test_package、真机编译+链接+安装 + 两层 test_package
  断言（ABI 3 条 + GCOBOL 前端端到端 7 条）全部通过。
- 上游测试口径：libgcobol 无独立测试套件，完整 COBOL 语义测试 = GCC 顶层
  `gcc/testsuite/cobol.dg`（464 项，GCOBOL 前端编译 + libgcobol 运行）。该 464 项已在
  feat/gcobol-16.1.0 真机逐项真实跑通（PASS 450 + XFAIL 13 + FAIL 0 + SKIP 1），是
  libgcobol 运行时的完整覆盖证据；本包 test_package 以「ABI + 端到端 COBOL 程序」作为
  消费验证。
- issue 编号：待补（本轮未在项目内找到明确 issue 编号）。
