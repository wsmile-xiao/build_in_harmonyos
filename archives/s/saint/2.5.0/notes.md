# saint 2.5.0 适配笔记

## 上游信息
- 官方项目页：http://saint-apms.sourceforge.net/Main.html（SourceForge，saint-apms）
- SAINT（Significance Analysis of INTeractome）：分析 AP-MS（亲和纯化质谱）蛋白互作数据的 C 工具集
- 官方源码归档：https://sourceforge.net/projects/saint-apms/files/SAINT_v2.5.0.zip/download
- sha256：fc9de49685ed92df49e1167d54719f8aec988342374a86909dc16960de638b51（对官方 /download 归档实测）
- 归档内容：SAINT_v2.5.0/ 源码 + __MACOSX/ 垃圾目录 + 预编译 bin/（勿用）

## 构建系统
纯 Makefile，无 configure：
- 顶层 Makefile：`CC = gcc`、`CFLAGS = -g -O3`、`LIBS := -lm -lgsl -lgslcblas`
- `TOPDIR := $(shell pwd)`，`TARGET=bin`、`BUILD=build`、`SRC=src`
- 产出 5 个可执行：saint-reformat / saint-spc-noctrl / saint-spc-noctrl-matrix / saint-spc-ctrl / saint-int-ctrl
- 每个工具 target 编译 `src/<subdir>/*.c *.h` → 多文件单次 `-c`（.o 落 cwd，`mv *.o build`，链接 `build/*.o`，`rm build/*.o`）
- 硬依赖 GSL：`gsl_rng_alloc` 等（-lgsl -lgslcblas -lm）

## 关键适配决策
1. **依赖**：`self.requires("gsl/2.8")`（仓库内 built 配方，共享库）。Makefile 固定 `-lgsl -lgslcblas`，与 gsl 配方 `libs=[gsl,gslcblas]` 一致。
2. **R33 编译器/路径**：CC 从 `tools.build:compiler_executables:c` 取（profile 指向 /data/service/hnp/bin/clang）；GSL 的 `-I`（编译需要 `#include <gsl/gsl_rng.h>`）与 `-L` 从 `dependencies["gsl"].cpp_info` 取；全部经 make 命令行变量覆盖（命令行变量优先于 Makefile 内赋值）。
3. **不走 `make all`**：`all` 末尾触发 `clean` 的 `rm $(SRC)/*/*.gch`。多文件 `-c` 可能不产 .gch，此时 glob 不匹配 `rm` 报错 → make 失败。改为按 5 个工具 target 逐个构建（自包含编译+链接）。
4. **zip 清理**：`source()` 剔除 `__MACOSX/` 与预编译 `bin/`，确保全量源码构建。
5. **R9 单作业**：`make -j1`（HMDFS 上并行 make 撞 jobserver fifo）。
6. 逐工具 `copy` 到 package bin/，`package_type="application"`、`cpp_info.bindirs=["bin"]`（R38 软件级 commands.json 已建）。
6.1. **R39 -fcommon（编译失败修复）**：真机 conan create 链接 saint-spc-noctrl 等工具时 ld.lld 报 `duplicate symbol: burn/iter/freq/freqgroup/modelvar/NORMALIZE`（dpalphaIP.o 对 setsummary/setprior/setparam/saint.o 等）。根因：saint.h 对这几个全局变量一律按"无 extern 的 tentative definition"声明（245-250 行），且每个 .c 都 `#include saint.h`、Makefile 用 `*.c` glob 各自独立 `-c` 成 .o。gcc 默认 `-fcommon` 在链接期把同名 tentative 定义合并成 common symbol → 上游 gcc 正常；clang15+ 默认 `-fno-common`，每个 .o 变 .bss 强定义 → duplicate symbol。修法：CFLAGS 加 `-fcommon`（本机用真实上游源码 + clang 复现：无 -fcommon 报 identical multiple definition，加 -fcommon 后同名全局合并、错误消失）。不影响上游源码正确性。
7. **R38 逐目标构建前必须 `make makeDirs`**：`build/` 与 `bin/` 目录只由 `makeDirs` 目标创建（是 `all` 的前置）；逐目标构建不经过 `all`，直接 `mv *.o $(BUILD)` 会报 "build not directory"（真机实测）。故 build() 先 `make makeDirs` 再逐个工具 target。

## 上游测试审计
- 归档 106 文件，5 个子目录均只有 .c/.h + compile 脚本，无 test/ 目录、无 make check、无 gtest/pytest/criterion。
- 结论：**上游无测试框架**（upstream_tests_exist=false），test 阶段输出 `HMBS_UPSTREAM_TEST_RESULT` no_tests 审计标记。

## test_package（自建功能验证，11 断言）
在 conanrun 环境运行（VirtualRunEnv 注入 gsl libdir 到 LD_LIBRARY_PATH）：
1-5. 5 个可执行已安装且可执行
6. saint-reformat -v 输出 "SAINT version 2.5.0"
7. saint-reformat 用最小 AP-MS 数据（interaction/prey/bait 3 个文件）真实重排，校验 interaction.new 非空且含预期行
8-11. 4 个 MCMC 工具以"过少参数"触发 usage（能走到 commandLine 即证明 GSL 链接可运行）

说明：MCMC 全量运行需真实大数据集且小时级，不纳入 test_package（只在 usage 冒烟）；saint-reformat 的轻量重排可完整跑通，作为核心功能验证。

## 真机验证（内部基建，勿写入 PR 正文）
- 环境：HarmonyOS PC 真机，/data/service/hnp 工具链 + conan 2.30，与官方 CI 同源
- 预检命令与官方 CI 一致：conan create（profile ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8，clang15，libc++，tools.build:jobs=1）
- 待真机预检验证：①多文件 `-c *.c *.h` 在 clang 下是否产 .gch / 个别工具是否正常；②saint-reformat 最小数据是否产出 interaction.new；③共享库 libgsl.so 运行时解析
- 真机测试数字将据此回填 .hmbs/pr-body.md「测试用例通过率」
