# libamplsolver 0-20190702 适配笔记

## 基本信息

- **三方库名称**：libamplsolver（AMPL Solver Library / ASL）
- **Conan 包版本**：0-20190702（连字符；对应 netlib ampl/solvers 2019-07-02 快照）。
  注意：上游 Debian pool 归档**文件名**为 libamplsolver_0~20190702.orig.tar.xz，其中的
  `~` 是 Debian 版本分隔符，**只出现在下载 URL/文件名，不进入 Conan 引用名**——
  Conan 2 拒绝包版本含 `~`（`ERROR: Invalid package version '0~20190702'`，E563）。
- **上游源码**：Debian 官方源（deb.debian.org），netlib https://ampl.com/netlib/ampl/
- **适配路径**：路径 A（基础适配，交付 archives/ 适配包）
- **使用知识库**：integration-skill（编译 SKILL）+ knowledge/ 同类 raw-Makefile 经验

## 库介绍

AMPL（A Mathematical Programming Language）求解器接口库：提供读取 AMPL 通用输出
`.nl` 文件、写入解 `.sol` 文件的例程，帮助自定义求解器与 AMPL 集成。纯 C 实现，
无第三方依赖。

## 构建系统

- **构建系统**：传统 raw Unix Makefile（makefile.u 变体）
- **关键点**：上游只提供 `makefile.{u,vc,lc,sy,wat}`，**没有默认 `Makefile`/`makefile`**，
  直接 `make` 会因找不到 makefile 而失败，必须 `make -f makefile.u`
- **目录**：make 必须在源码目录执行（`cwd=self.source_folder`），产物 `amplsolver.a`
  在源码目录就地生成
- **编译命令**：`make -f makefile.u CC=<clang> CFLAGS='-O2 -fPIC' -j1`
- **生成物**：`amplsolver.a`（静态库）+ 构建期生成头文件（arith.h、stdio1.h）+ 源码头文件（asl.h 等）
- **arith.h 生成**：`arith.h` 目标会编译并运行 `arithchk.c` 探针（`./a.out` 输出平台头文件），
  真机可运行

## OHOS 适配要点

1. **编译器获取**：R33，编译器从 Conan conf `tools.build:compiler_executables` 获取
2. **makefile 缺失**：必须显式 `make -f makefile.u`，不能裸 `make`
3. **cwd**：raw Makefile 产物就地生成，须 `cwd=self.source_folder`
4. **PIC**：`-fPIC` 静态库便于链接进共享库
5. **库名**：产物为 `amplsolver.a`（无 `lib` 前缀），`package()` 改名为 `libamplsolver.a`，
   下游才能用标准 `-lamplsolver` 链接（`cpp_info.libs = ["amplsolver"]`）
6. **-j1**：R9，老 makefile 单线程，用 `-j1`

## 上游测试审计（无自动化测试）

经审计上游源码与构建文件，**libamplsolver 0-20190702 没有任何自动化测试**：

- `makefile.u` 仅有 `all/arith.h/stdio1.h/details.c/systemprintf/xsum.out/clean` 目标，
  **无 `check`/`test`/`TESTS`/`check_PROGRAMS` 目标**
- `xsum.out` 仅为传输校验（依赖外部 netlib `xsum` 程序），不是测试套件
- 无 `tests/`、`test*` 目录，无 CI 配置，无测试框架接入
- `make -n check` 无对应规则

故 test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` + 完整 `upstream_test_audit`，
上游测试标记 `status: no_tests`、`discovered:0 / executed:0`。

## 依赖

- 无编译依赖，无运行依赖

## test_package（新增消费者测试）

对打包库调用真实 ASL API 做 6 项断言（`test_ampl.c`）：

1. `ASL_alloc(ASL_read_pfgh)` 分配成功
2. `asl->i.ASLtype == ASL_read_pfgh`（库写入）
3. `asl->i.n_prob == 1`（库写入）
4. `asl->p.Objval` 函数指针已接线（真实求值例程）
5. 空模型 `n_var_ / n_con_ == 0`
6. `ASL_free(&asl)` 将指针置空

## 验证结果

- 编译状态：本地 Linux/gcc 已验证构建与链接逻辑；真机（HarmonyOS aarch64）待 hmbs 预检
- 上游测试用例通过率：N/A（上游无自动化测试，`no_tests`）
- 新增测试用例（test_package）：6 项真实 API 断言
- 备注：`ASL_alloc`/`ASL_free` 为企业真实 API（不是 `asl_alloc`/`asl_free`）

## 补充说明

1. **版本号**：Conan 包版本为 `0-20190702`（连字符），对应 netlib ampl/solvers 2019-07-02
   快照。Debian pool 的归档文件名为 `libamplsolver_0~20190702.orig.tar.xz`——`~` 是 Debian
   版本分隔符（表示 early-than），但 Conan 2 拒绝包版本含 `~`（E563），故版本归一化为
   `0-20190702` 与归档目录/分支/各 manifest 一致；`~` 仅保留在下载 URL/文件名中。
2. **源码镜像**：conandata.yml 提供有序镜像列表（aliyun/tuna/ftp.debian.org 在前，
   官方 deb.debian.org 最后回退），sha256 恒定 `85b05cd...`，已逐一对齐校验
3. **测试范围**：上游无测试，由 test_package 做消费者视角的真实 ASL API 验证

## 补充：shared 选项修复（真机失败轮）

真机 preflight 在 "Computing dependency graph" 阶段失败：
`ERROR: libamplsolver/0-20190702: Package type is 'library', but no 'shared' option declared`。

根因：conanfile 声明了 `package_type = "library"`，但缺少 Conan 2 对 library 类型强制要求的
`options = {"shared": [...]}` / `default_options`。图计算阶段即中止，build/test_package 均未执行；
日志中的 `/tmp: Read-only file system` 来自 preflight.sh 包装脚本自身（hmbs 侧），非本配方触发。

修复：在 conanfile 增加 `options = {"shared": [True, False]}` 与 `default_options = {"shared": False}`，
并在 `validate()` 中对 `shared=True` 抛 `ConanInvalidConfiguration`（上游 makefile.u 仅产出静态
`amplsolver.a`）。未改动测试口径与 no_tests 审计。
