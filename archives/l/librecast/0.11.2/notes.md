# librecast 0.11.2 适配笔记（前置适配轮）

## 状态

- **本轮为前置适配**：W0 依赖检查、源码/构建系统分析、Conan 配方与 test_package 准备、
  7 个 OHOS 预处理补丁（dry-run 验证通过）均已完成。
- **真机构建未执行**：阻塞点是依赖 `lcrq` 尚未发布到制品仓（见下）。
- manifest 状态：`pending`，真机验证后更新为 `built`/`published`。

## 上游概况

- 项目：Librecast Project（IPv6 组播库），官方仓库 https://codeberg.org/librecast/librecast
- 版本：0.11.2（configure.ac AC_INIT 确认），ABI 版本 0.6（SONAME librecast.so.0.6）
- 许可证：GPL-2.0-only OR GPL-3.0-only
- 构建系统：autotools（configure.ac 2.71 + 预生成 configure + 手写 Makefile.in 层级：
  顶层 → src / test / doc / examples / libs/{blake3,libmld}）
- 产物：仅共享库 `librecast.so`（无静态库目标），头文件 `librecast.h` + `librecast/*.h`

## 源码获取

- 上游**未发布独立 release tarball**：librecast.net/release/ 已 404（新/旧版本路径均试过），
  Codeberg 与 GitHub 镜像均无 release assets。
- 采用官方 Codeberg 仓库 `v0.11.2` tag 自动归档（权威官方源，符合 R39）：
  `https://codeberg.org/librecast/librecast/archive/v0.11.2.tar.gz`
- sha256：`62dd9c3250c8e3ef30ed66aa82060d8651e3e887a085079431aa71d4232ce49c`
  （两次独立下载交叉验证一致，Gitea 归档对同一 commit 确定性生成）
- 注意：归档内含符号链接（`test/all/*.test → ../` 与 `test/enc/` 等）。
  真机 Linux 解包正常；Windows 本机解包会丢符号链接（仅影响本机分析，不影响配方）。

## W0 依赖检查结论

| 依赖 | 性质 | 制品仓状态 | 处理 |
|------|------|-----------|------|
| lcrq 0.4.1（RaptorQ FEC） | **硬链接依赖**（见下） | ❌ 未发布（ohpcd 查询 0 条） | **先拆 lcrq 独立适配**（issue/分支/PR），本 PR 声明依赖 |
| libsodium | 可选（加密），configure 默认探测 | ✅ 1.0.20 / 1.0.22 已发布 | requires libsodium/1.0.22 |
| blake3 | 内置（libs/blake3，源码已 vendored） | 不需要 | 随主库构建 |
| libmld | 内置（libs/libmld，AC_CONFIG_SUBDIRS 子构建） | 不需要 | 随主库构建 |

**lcrq 为何是硬依赖**：INSTALL.md 自称 optional，但 `src/Makefile.in:41` 无条件
`LIBS += -llcrq`——即使 configure 探测失败（LIBLCRQ 为空），链接 librecast.so 时仍会
`-llcrq`，直接链接失败。0.11.2 实际无法在无 lcrq 环境下构建。

## 本机已完成的前置工作

1. worktree `D:\harmonyos\worktrees\librecast`，分支 `feat/librecast-0.11.2`
   （基于 origin/main f8f47d0d17 快进）。
2. 源码下载 + sha256 确定性验证（两次下载一致）。
3. 构建系统分析（见 `reports/W0-report.md`）。
4. 7 个补丁（`patches/`，全部对原始源码 dry-run 验证通过）：
   - 0001/0002：顶层 config.guess/sub 加 HarmonyOS 识别（复用 `scripts/patch-autotools-ohos.pl`）
   - 0006/0007：libs/libmld 子目录的 config.guess/sub（AC_CONFIG_SUBDIRS 独立副本）同样处理
   - 0003：顶层 `install: all doc` → `install: all`（OHOS 无 coreutils `install`，man 页
     安装必挂，libfec 先例；Conan 包亦无需 man 页）
   - 0004/0005：`ln -sf` → `cp -f`（构建期 soname 别名 + 安装别名；真机文件系统符号
     链接受限，避坑指南 #15；cp 与 ln 等价满足测试/运行时需求）
5. conanfile.py / conandata.yml / test_package（实质 API 调用 + 可观察断言）。

## 配方关键决策

| 决策 | 原因 |
|------|------|
| `basic_layout(build_folder=".")` 强制 in-tree | 上游 Makefile 非 VPATH 感知（src/Makefile.in `-I../include`），out-of-tree 必挂 |
| `options = {"shared": [True]}` | 上游只产出共享库，无静态目标；不提供虚假的 shared=False |
| `requires lcrq/0.4.1` | 硬链接依赖（见上）；先拆 lcrq PR，本 PR 等其合入后验证 |
| `requires libsodium/1.0.22` | ohpcd 已发布；沿用 et/mkp224o/minisign 的 bare-ref 惯例 |
| build() 末尾 `make test`（全量） | 上游官方入口；测试框架自带 WARN 优雅跳过（见下） |
| `-j1` | 与仓库 autotools 惯例一致，规避 jobserver/HMDFS 并发问题 |

## 上游测试分析（L2 依据）

- 全集：`test/????-????.c` **126 个**独立用例 + `libs/libmld/test` **11 个**（blake3 的
  test 为上游空目标）。断言总数 ≈ 1300 + 133（grep 统计）。
- runner：`maketest`（无 lctest 时），逐用例运行；退出码语义：
  `0=PASS, 1=WARN(跳过), 2=FAIL, 其他=UNKN`，任一 ret>=2 才算失败。
- 平台自适应：
  - 网络用例 `test_require_net()` 检测组播路由/IPv6 等级，不满足 → `exit(TEST_WARN)` 优雅跳过。
    真机无组播路由时预期大量 WARN（不算失败）。
  - 权限用例 `test_cap_require()`：非 root 时 `capfail++`，`test_name()` 阶段提前退出(0)。
- 裁剪预案（真机超时/平台性 FAIL 时启用，结果如实记录）：
  `make -C test maketest TEST_PROGS="0000-0000.test 0000-0002.test ..."`（纯 API 子集）。

## 真机风险清单（首轮验证重点关注）

| # | 风险 | 预案 |
|---|------|------|
| 1 | lcrq 依赖缺失 | 先完成 lcrq 独立适配并发布（本轮外） |
| 2 | libmld 子构建 `SHELL := bash`（libs/libmld/Makefile.in） | 真机确认 `command -v bash`（避坑指南 十-2） |
| 3 | 归档解包符号链接失败 | conan 缓存位于数据分区一般支持；若失败改用 tar 解包诊断 |
| 4 | `install` 命令缺失 | 已由补丁 0003 规避 man 页路径；src 安装用 `@INSTALL@`（AC_PROG_INSTALL 回退 install-sh） |
| 5 | configure 需要 `sh`（CONFIG_SHELL） | Autotools.configure 走 conan env；必要时 profile 注入 CONFIG_SHELL=/bin/sh |
| 6 | 全量测试时长 | 126+11 用例，部分含 sleep/超时；超时则用 TEST_PROGS 子集 |
| 7 | 依赖探测失败（-lsodium/-llcrq 找不到） | AutotoolsToolchain 会把 conan 依赖的 libdir/include 注入 LDFLAGS/CPPFLAGS；真机先 `conan profile show` 校验 compiler_executables 为合法 dict |

## 下一步（真机 / shadow CI）

前置条件：lcrq 独立适配 PR 合入且 `lcrq/0.4.1` 发布到 ohpcd。

1. 真机单包验证（隔离 runner，按 `真机链接知识库/openharmony-pc-native-shadow-ci.md`）：
   ```sh
   # SSH 进真机后，确认工具与临时目录（避坑指南 十-1/2/3）
   command -v sh git conan clang clang++ bash; echo "$PATH"
   # 单包构建（Conan 隔离 CONAN_HOME + 项目 settings.yml/profile）
   CI_PACKAGES="archives/l/librecast/0.11.2" bash ci/conan/build_and_test.sh
   # 或 shadow CI 运行器单包入口
   /path/to/run-ohos-shadow-ci.sh archives/l/librecast/0.11.2
   ```
2. 通过标准（工作流 §4）：Build Summary `Total: 1`；L0/L1 pass；L2 记录 PASS/WARN/FAIL
   明细（网络类 WARN 属预期）；L5 确认 `lib/librecast.so*` 真实存在。
3. 失败时：按避坑指南 §13 排查顺序（连接→传输→隔离→日志→TMPDIR→profile→符号链接→RPATH）。
4. 验证通过后：`conan-verify`（G1-G4，产出 reports/quality-report.md）→ 更新 manifest
   状态 → W4 pre_pr_audit → 推送 fork → GitCode 网页建 PR（标题
   `feat(librecast): 0.11.2 编译完成`，描述含依赖 PR 链接）。

## 依赖 PR 声明（PR 模板用）

```text
依赖 PR：<lcrq 独立适配 PR 链接（待创建：feat/lcrq-0.4.1）>
当前 PR 等 lcrq 合入/制品发布后再做最终真机验证。
```

## 参考实现

- `archives/l/libfec/1.0`：同为 autotools + config.guess/sub 升级 + install 规则 OHOS 化
- `archives/l/libsodium/1.0.22`：依赖包本体（已发布）
- `archives/m/minisign/0.12-r1`：libsodium/1.0.22 bare-ref 消费方惯例
