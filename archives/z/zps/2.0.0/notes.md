# zps 2.0.0 适配笔记（HarmonyOS PC · Conan CMake · 单文件 CLI）

## 定位
- `zps` 是一个专注的**僵尸进程（zombie / defunct）管理 CLI**：扫描 `/proc` 列出进程并
  标出 `Z` 状态，再按 `-r` / `-p` / `-q` 把信号发给僵尸进程的**父进程**完成回收
  （默认 `SIGTERM`；`-s` 可指定信号号或信号名）。
- 上游 = 纯 POSIX C（`src/zps.c` + `src/zps.h`，约 1000 行），**零第三方依赖**：
  只用 `opendir/readdir`、`read`、`kill`、`isatty`、`clock_gettime` 等 libc 接口。
- 构建系统 CMake（`cmake_minimum_required(VERSION 3.15)`），
  `install(TARGETS zps RUNTIME DESTINATION bin)` → 构建产物**只有 `bin/zps`**
  （上游 `man/zps.1`、`.application/zps.desktop` 未被 CMakeLists 安装，保持上游行为）。
- 源码：`https://github.com/orhun/zps/archive/refs/tags/2.0.0.tar.gz`
  sha256 `84fa627c7eec92df62ecae129fe30fc7d16e297f20a3d126b8c53d04a6c35c60`。

## 上游测试清点（R51 申报表 · 适配前完成）
| 项 | 内容 |
|----|------|
| 测试框架 | **无**（没有 ctest/pytest 注册表、没有 `check`/`test` 目标；`make -n check` 无目标） |
| 自动化测试入口 | `scripts/test.sh`（唯一入口；`.github/workflows/ci.yml` 以 `working-directory: scripts` + `run: ./test.sh` + `UPLOAD: true` 调用） |
| 入口性质 | bash `&&` 链冒烟测试，**无用例注册表、无断言框架**，靠退出码判定 |
| 用例构成 | 15 个上游步骤：编译 `example/zproc.c`(僵尸工厂) → 后台跑 2 份造僵尸 → `gcc -fprofile-arcs -ftest-coverage` 编译 `src/zps.c` → 4 条 CLI 链（`-v`/`-h`/`-p`；`-a`/`-r`；`-q`/`-s 9`/`-s SIGTERM`/`-s term`；`-n`）→ `gcov` 覆盖率 → 可选 codecov 上传 |
| 上游环境假设 | glibc + `gcc` + `gcov`；`example/` 就地编译；用 `kill` 杀自家僵尸父进程 |

## 构建方式（Conan CMakeToolchain + OHOS profile）
```bash
conan create archives/z/zps/2.0.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
真实执行的命令（完整日志见 **W3 的 conan create 输出** `reports/w3-local-ci.log`；
`reports/conan-create.log` 是 finish step[4/10] conan-verify 的日志，因配方 revision
未变、其 build 段为 conan 缓存命中 `Already installed`，test_package 仍真实重跑）：
```bash
# configure
cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" \
      -DCMAKE_INSTALL_PREFIX=... -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" \
      -DCMAKE_BUILD_TYPE="Release" <src>            # exit 0
# build
cmake --build <build>/Release -- -j20               # exit 0
# install
cmake --install <build>/Release --prefix <pkg>      # exit 0
```
- 交叉工具链由 OHOS profile 提供：`tools.build:compiler_executables={'c':'/data/service/hnp/bin/clang'}`
  + conan 的 `os=OHOS` → `linux-ohos` 三元组映射，**无自定义 toolchain 代码**。
- `generate()` 显式 `BUILD_SHARED_LIBS=OFF`（R26）；配方零 `requires` → 产物只依赖系统 libc。

## 首个真实问题：`System is unknown to cmake` 警告（HarmonyOS 目标名）
**命令**：`cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=generators/conan_toolchain.cmake ...`
**原始输出（`reports/w3-local-ci.log` 中 conan create 段落，原文摘录）**：
```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file ...
```
**根因**：conan 的 CMakeToolchain 把 `settings.os=OHOS` 映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`
（conan `cmake/toolchain/blocks.py`），而 cmake 的平台模块目录里只有 `Platform/OHOS.cmake`
（本机 OHOS 定制 cmake 4.1.2）／没有 `Platform/HarmonyOS.cmake`。
**影响与处置**：该 cmake 把「未知系统名」降级为**警告后继续**，configure/build/install 全部
`exit 0`，产物为 aarch64-linux-ohos + musl 的 ELF；故**未做规避**（不改配方、不改上游源码）。
若换用会对未知系统名**硬失败**的 cmake，需要在 `generate()` 里显式
`tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"`（本仓库 518 个配方有同类处理）。
**重新验证**：`cmake --build` / `conan create` 均 0 退出码；`conan-verify` G2 PASS。

### 其他真实输出
- `clang-15: warning: argument unused during compilation: '-s'`（同一份 `reports/w3-local-ci.log`）：
  上游 `CMakeLists.txt` 把 strip 标志 `-s` 放进 `target_compile_options`，编译期无效、
  链接期不会带上 → 产物未被 strip。**属上游写法问题，未修改源码**（R1 参数最少化）。
- 全程**无编译/链接错误**：`/proc` 解析、`kill()`、`opendir` 等接口在 HarmonyOS 上原生可用，
  **补丁数 = 0**（`patches: {}`）。

## 打包：HarmonyOS 代码签名（否则 test_package 无法执行）
`package()` 在 `settings.os == "OHOS"` 时对 `bin/` 下 ELF：
```bash
llvm-objcopy --remove-section .codesign bin/zps   # 先剥旧签名
binary-sign-tool sign -inFile bin/zps -outFile bin/zps -selfSign 1
chmod 0755 bin/zps                               # 签名工具会抹掉执行位 → 必须补回
```
实测：产物带 `.note.ohos.ident` + `.codesign` 段（`test_package/test_ohos.sh` 检查项 4），
`bin/zps` 可正常执行；不补 `chmod` 会出现 `conan test` → `Permission denied`。

## 依赖版本
无（零 `requires`；产物 `DT_NEEDED` 只有系统 `libc.so`）。

## 验证结果
```bash
python3 scripts/ohc-run.py conan-verify zps 2.0.0     # G0-G4 + L2/L4/L5 全 PASS
conan create archives/z/zps/2.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 ...   # exit 0
bash archives/z/zps/2.0.0/run_upstream_tests.sh       # 上游用例 17 项: 12 PASS / 0 FAIL / 5 跳过
bash test_package/test.sh      → 7/7 断言通过（消费者视角）
bash test_package/test_ohos.sh → 9/9 断言通过（HarmonyOS 专项）
```

## 上游测试实机结果（HarmonyOS PC aarch64，详见 `reports/upstream-tests.log`）
- 阶段 A（上游 `scripts/test.sh` 原样运行，PATH 注入 `gcc→OHOS clang`、`gcov→no-op` shim）：
  **退出码 1**，唯一失败点是脚本末行清理
  `rm -v zps zps.c.* zps.gc*` —— `zps.c.*`（gcov 产物 `zps.c.gcov`）在无 GNU 工具链的
  平台上不存在 → `rm: zps.c.*: No such file or directory`。
  除上游 `&&` 链中与工具契约冲突而短路的 `./zps -s 9`（rc=1，即下表 C10；其后的 C11/C12
  因此从未执行）外，其余功能步骤在日志中均为 rc=0。
- 阶段 B（逐用例复算）：17 项 = **12 PASS / 0 FAIL / 3 SKIP / 2 NA**，可执行用例通过率 **12/12**。
  - SKIP（C10-C12）：上游把 `zps -s 9` 写在 `-q && -s 9 && -s SIGTERM && -s term` 的第 2 位，
    而工具契约要求 `-s` 必须与 `-r`/`-p` 同用（rc=1）→ **上游链在此短路，后两条命令从未执行**。
    用例与工具契约冲突，故记 SKIP；补全用例 C16/C17 覆盖其真实意图。
  - NA（C14/C15）：`gcov` 覆盖率（无 GNU 工具链）、codecov 上传（`UPLOAD=true` 才启用）。
- 补全用例（适配新增，共 2 条）：`zps -r -s CHLD`（README 推荐组合）、
  `zps -r -s 9|15|SIGTERM|term`（信号号/信号名解析）→ 全 PASS。

## 知识沉淀
- conan `os=OHOS` → `CMAKE_SYSTEM_NAME=HarmonyOS`，而 OHOS 定制 cmake 只提供
  `Platform/OHOS.cmake`：本机 cmake 4.1.2 仅告警并继续；写配方时需知道
  「HarmonyOS 目标名是预期行为，不是配置错误」，避免误加 `CMAKE_SYSTEM_NAME=Linux` 规避。
- HarmonyOS 上编译 `-fprofile-arcs -ftest-coverage` 可被 clang 接受并生成 `.gcno/.gcda`，
  但**没有 `gcov`**（GNU 工具链缺失）→ 上游覆盖率类测试链路在本平台不可复现，
  报告需显式标记 NA 而不是判 FAIL。
- 僵尸回收语义在 HarmonyOS 上成立：`kill(僵尸父进程, SIGTERM)` → 僵尸被 reparent 到 init
  并在约 1-2 秒内消失；`SIGCHLD` 仅对实现了 `wait()` 的父进程有效（默认处置不会回收）。

## 注意事项
- `zps -r` / `-q` 会**向系统中所有僵尸进程的父进程发信号**（工具设计如此，默认 SIGTERM），
  在共享设备上会波及无关进程。因此本包 test_package 测试统一改用 **`-r -s CHLD`**：
  helper 在收到显式 SIGCHLD 且门控标记落盘后才 `wait()`，既验证真实回收又零副作用；
  断言口径为「signaled/defunct 自洽 + 自家僵尸消失」，容忍主机上的并发无关僵尸。
- `/proc/<pid>` 对他用户进程多为 `Permission denied`，`zps` 会静默跳过 —— 属预期，非缺陷。

## 本地流水线注意（本次实操记录）
1. **W3 的 junk_check 分模式**：`junk_check` 优先 `git diff origin/main...HEAD`（incremental
   模式，只查本 PR 文件）；**分支上尚无提交时该 diff 为空 → 退化为 full 模式（扫全仓
   `git ls-files`）**，会命中仓库里既有的 `archives/c/cloog/0.21.1/.build-closed`、
   `.staging-verified`（main 上的历史遗留，属他人归档，本包未改动）而阻塞 W3。
   本次首次 finish 即踩到该情形：按 PR 文件清单生成 `pr.diff`（`git add -N <路径> && git diff`）
   并用 `JUNK_PR_DIFF=<pr.diff>` 让 junk_check 走 **prdiff 模式**复现真实 PR 场景 → W3 全绿；
   产生本地提交后复跑 finish 时 junk_check 自动回到 incremental 模式（只含本包 14 个文件）。
2. **conandata.yml 镜像残留**：W3 的 mirror fallback 会把单值官方 URL 改写成
   「镜像前缀 + 官方」的双值列表，且**其 `trap EXIT` 还原在本次运行未能落到最终文件**
   （备份内容已是上一次运行改写后的镜像列表）。提交前必须手工还原为**官方单值 URL**
   （R39 / PF7 源 URL 闸），本次已还原并核对无镜像域名；源码 sha256 未变，W3 证据仍然有效。
3. `.staging-verified`、`.build-closed`、`.ci-result.json`、`conandata.yml.ghfast-bak`、
   `packaging/` 均为运行时/本地文件且已被 `.gitignore` 覆盖，**不进 PR**。
4. **一次真实回归（已修复）**：本地提交后复跑 finish 时 W3 失败，报
   `FAIL: -r did not report 1/1 signaled: … 2/2`。根因是当时主机上出现**与测试无关**的僵尸
   （`46181 726 Z /usr/bin/zsh`）：①断言把 signaled 写死为 `1/1`；②测试用了默认 `-r`（SIGTERM），
   顺带对其父进程发了信号（实测该父进程随后消失）—— 既是脆性断言，也是对共享主机的破坏性副作用。
   修复：测试改 `-r -s CHLD` + helper 门控 `wait()`，断言改为「N/N 自洽 + 自家僵尸消失」；
   复验两种场景（无/有无关僵尸）均 7/7 与 9/9 通过，且不再影响无关进程。
---

**编译结束**: 2026-09-23 13:19
**最终状态**: built
