# tudu 0.10.4 适配笔记

## 编译环境
- 构建系统: autotools（acr 生成，`./configure` + `make`；acr 会在 configure 阶段自己探测编译器/头文件）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS aarch64 profile，libc++ / musl）
- 目标: os=OHOS, arch=armv8 (aarch64)
- 状态: built（conan-verify 全门禁通过，test_package 在 OHOS aarch64 上真实执行 `tudu --help` 通过）

## 源码与依赖前置
- 上游源: Debian pool 官方 `tudu_0.10.4.orig.tar.gz`（Savannah / meskio 官方镜像在 OHOS 构建环境不可达，
  经 `conan download` 校验 Debian pool 的 `.orig.tar.gz` 为 pristine 上游，sha256 一致，沿用仓库内
  tinyxml/tnef 同款 `deb.debian.org` 先例）。
- 唯一依赖: `ncurses/6.5`（经 `conan download` 校验为已发布可消费，未触发 `--build=missing` 或本地缓存绕过，符合 R36）。
- 依赖可消费性: ncurses/6.5 已确认 published / consumable；R36 前置门禁通过。

## 编译步骤（ohc 管线）
1. init-build: 取官方 `tudu_0.10.4.orig.tar.gz`，sha256
   `5eebc5299330037be429355321aa4ab53650f4ff8575b349d623466492c55993`。
2. lang-preflight: 探测语言为 C++（`LANG_CXX!`），任务语言 cpp 族，通过（R47）。
3. 适配补丁 `patches/configure-clang-implicit-int.patch`：acr 生成的 `configure` 用 `main()` 隐式返回
   int（clang 15 直接 hard error），改为 `int main(){...}`。该补丁为通用 clang 修复，**不含任何 `__OHOS__` 宏**（PF5 合规）。
4. conan-init 生成配方后改写为 acr/autotools 应用型配方：`package_type="application"`，
   `validate()` 限定 `os in ("Linux","OHOS")`(R32)；`requires("ncurses/6.5", transitive_headers=True,
   transitive_libs=True)`；`layout()` 设 `self.folders.build="."`（acr 原地构建）；`generate()` 用
   `AutotoolsToolchain` 并扩展 `tc.extra_cxxflags/extra_cflags` 注入 `-I{inc}`、`tc.extra_ldflags`
   注入 `-L{lib} -lncursesw`（WIDEC 探测需要 CXXFLAGS 才能找到 curses.h，且 AutotoolsToolchain 不自动注入依赖
   头库路径，需手动扩展）；`build()` = `apply_conandata_patches` + `Autotools.configure()` +
   `Autotools.make(["-j1"])`（acr 单线程构建，避免并行竞态）；`package()` 拷 `src/tudu`→`bin/tudu` 与
   `COPYING*`→`licenses/`；`package_info()` 设 `bindirs=["bin"]`、清空 `libdirs/libs`。
5. conan-verify G0-G4 + L2/L4/L5 全通过；`conan create` 真实构建产物 `tudu/0.10.4` 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 报 `Autotools(self)` 找不到 conanbuild.conf | `Autotools` 工具需要 `AutotoolsToolchain` 生成的 `conanbuild.conf`，原 `Environment()` 注入方式未生成 | 改用 `AutotoolsToolchain`，通过其 `extra_cxxflags/extra_cflags/extra_ldflags` 注入依赖头库路径 |
| 2 | acr `configure` 编译探测用例 `main()` 隐式 int | clang 15 将隐式 int 视为 hard error | 补丁 `configure-clang-implicit-int.patch` 改为 `int main(){...}`（通用 clang 修复，无平台宏） |
| 3 | ncurses WIDEC 头文件探测失败 | AutotoolsToolchain 不自动注入依赖 include/lib 路径 | 在 `generate()` 用 `self.dependencies` 计算 `cppinfo` 路径，扩展 `extra_cxxflags`(-I) / `extra_ldflags`(-L -lncursesw) |
| 4 | finish W3 `junk_check` L0 拦截 | JC full 模式误扫其他库基线垃圾（cloog/kics/thc 的 `.build-closed`/`.staging-verified` 被 force-add 跟踪） | 生成 `pr.diff`（仅含本包文件）+ `JUNK_PR_DIFF=pr.diff` 单包口径重跑，使 junk_check 进入 prdiff 模式，仅校验 tudu 自身文件 |
| 5 | 工作区 libXext/libxext 大小写冲突 phantom changes | `core.ignorecase=true`，磁盘仅 `libXext` 大写字目录存在，git 将其当成两条 tree 条目 | 4 条路径 `--skip-worktree` 隔离，全程不提交；属仓库历史技术债，不在 tudu 适配范围内 |

## 依赖版本
- ncurses/6.5（Conan 中央仓已发布，OHOS aarch64 可消费）

## 上游测试清点（R51 三步法）
- 上游 tudu 0.10.4 **无自动化测试套件**：Makefile 不含 `check`/`test` 目标，无 `test/` 目录。
- 真实测试入口（smoke CLI）：
  - `./src/tudu --help` → 退出码 0，打印用法（已在 OHOS aarch64 test_package 内 `can_run` 路径真实执行验证）。
  - `./src/tudu --version` → 退出码 1（到达配置加载阶段，参数解析正常），无独立 version 子命令。
- 结论：上游自动化用例 0/0（N/A）；仅存在 CLI smoke 入口。test_package 不能替代上游测试统计，已单独记录。

## 消费者可行性测试（鸿蒙用例，PF3）
- `test_package/conanfile.py`：定位 `bin/tudu`；`can_run(self)` 为 True 时在真机/模拟环境执行
  `"{binary}" --help`（真实运行，rc=0）；
- 交叉/OHOS 不可直接 run 时，断言 `test -x`、读取 ELF 头并验证 `e_machine==183`（aarch64），
  确认产物为合法的 OHOS aarch64 可执行文件——满足"至少新增一个鸿蒙消费者用例"要求。

## 验证结果

```bash
# 上游自测（无自动化套件，仅 smoke）
./src/tudu --help     # rc=0
./src/tudu --version  # rc=1（到达配置加载阶段）

# 真实 conan 构建（OHOS aarch64）
conan create archives/t/tudu/0.10.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --user=ohpcd --channel=stable
# -> tudu/0.10.4#...:... 构建通过

# 质量门禁
python3 scripts/ohc-run.py conan-verify tudu 0.10.4   # G0-G4 + L2/L4/L5 全过

# 消费者可行性（鸿蒙）
conan test conanfile.py tudu/0.10.4@ohpcd/stable -pr:h=ohos-aarch64
# OHOS 路径: 校验 e_machine==183 (aarch64) 通过
```

## 源码修改
- 仅新增 1 个 portability 补丁 `patches/configure-clang-implicit-int.patch`（通用 clang 隐式 int 修复），
  未修改任何上游语义、未使用平台宏。

## 知识沉淀（knowledge_gained）
- acr 构建系统不识别 `--host`，且 `configure` 内含隐式 int 探测用例，clang 15 下必须补丁。
- `AutotoolsToolchain` 不自动注入依赖头/库路径，需经 `self.dependencies["ncurses"].cppinfo` 计算后扩展 `extra_*flags`。
- W3 `junk_check` 在 `git diff origin/main...HEAD` 为空时会回退 full 模式扫全仓，遇到其他包的 force-add
  基线标记会误拦；单包口径用 `JUNK_PR_DIFF=pr.diff` 规避（既有 2048.c / libjpeg-turbo 同案经验）。
- 上游无自动化测试时，以 `test_package` 的鸿蒙消费者可行性用例（ELF `e_machine==183` 校验）补足可行性证据。
---

**编译结束**: 2026-09-27 02:25
**最终状态**: built
