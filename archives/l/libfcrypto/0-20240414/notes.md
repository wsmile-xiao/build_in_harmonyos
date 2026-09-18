# libfcrypto 0-20240414 适配笔记

## 当前状态

- 状态：built（目标：`conan create` 干净轮通过；制品尚未上传）
- 分支：`feat/libfcrypto-0-20240414`（平台任务 ID 13163，积分赛）
- worktree：`/storage/Users/currentUser/ws/worktrees/libfcrypto-0-20240414`
- 真机：OHOS aarch64（HarmonyOS，单端完成构建与测试）

## 版本号映射

- 平台任务版本：`0-20240414`（libyal soname-0 + 日期版本惯例；Debian 将同一
  发布记为 `libfcrypto_0~20240414`）
- 上游 tag：`20240414`（release 资产 `libfcrypto-alpha-20240414.tar.gz`）
- 上游 commit：`4c4d2e85981edbdbc9fcf9da9cd98e3fb8619b6c`
- 配方/目录/分支三处版本一致（PF8/PF9/L0n）；源码 pin Debian orig tarball
  （与官方 release 资产逐字节相同：同 629026 字节、同 SHA256、同顶层目录，
  2026-09-18 设备实测），GitHub release 资产 URL 记录于 manifest 的
  upstream_release_url。直接 github.com 下载在构建机间歇性超时（三轮验证中
  conan-verify 一次实测连接超时；libvhdi 同族先例相同），故 pin 字节相同的
  Debian 镜像。

## W0 依赖检查

上游 configure.ac 仅引用本地捆绑组件 `libcerror`（AX_LIBCERROR_CHECK_ENABLE，
发布包内自带 `libcerror/` 目录，以 libtool noinst 静态并入 `libfcrypto`），
无外部 Conan 依赖（`requires` 为空）。可选能力：

- Python 绑定（pyfcrypto）：显式关闭（`--disable-python`，上游默认即 no）；
- 无 libfuse/工具类可选依赖（libfcrypto 是纯库，无命令行工具）。

## W1 源码与构建系统

- 构建系统：Autotools（发布包自带 `configure`/`aclocal.m4`/`config.guess`/
  `config.sub`/`Makefile.in`，**不需要** autoreconf）
- 编译器：OHOS SDK clang（`ci/conan/profiles/ohos-aarch64`：
  os=OHOS、arch=armv8、clang 15、Release）
- 发布包闭包：配方在 `build()` 开头强制检查捆绑 `libcerror/` 目录与 5 个
  生成文件，缺失即 `ConanInvalidConfiguration`，不静默 bootstrap、不运行
  `synclibs.sh`。

## 配方设计

`archives/l/libfcrypto/0-20240414/conanfile.py`：

- `source()`：`get(..., filename="libfcrypto-alpha-20240414.tar.gz",
  strip_root=True, **conandata["sources"])` —— 显式文件名，避免 Conan 从
  URL 推断归档格式失败（BadZipFile 类问题）；
- `generate()`：`AutotoolsToolchain` + `--disable-python`；OHOS 下显式加
  `--build/--host=aarch64-unknown-linux-gnu`（见下方问题 #1；
  `--enable-shared/--disable-static` 由工具链按 `shared` 选项自动生成）；
- `build()`（OHOS）：闭包检查 → conandata 补丁（config.guess）→ umask 022 →
  改写 configure 内 `umask 077` → CONFIG_SHELL 显式执行 configure →
  `make -j2` → 上游测试 HOME 沙箱 → test_runner.sh 运行期适配 → 注入
  `libfcrypto/.libs` 的 LD_LIBRARY_PATH → `make -j1 check
  LOG_COMPILER="$CONFIG_SHELL"`。Linux 分支走 `autotools.configure()` +
  `make -j1 check`（不引入 HMDFS 适配）。
- `package()`：`make install DESTDIR=<package_folder>` + COPYING/COPYING.LESSER；
- `package_info()`：`libs=["fcrypto"]`，cmake/pkg_config 名设为 `libfcrypto`。

> **测试运行适配 vs 上游测试用例修改**：对 `tests/test_runner.sh` 的改动只是
> 让 libtool 包装脚本解析到真实 ELF、并让 automake 用 bash 跑 runner；
> **没有任何**上游测试用例（`tests/fcrypto_test_*.c`、断言与逻辑）被修改。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本 release 的 `config.sub`（2023-06-23）报 `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`，`config.guess` 同样不能识别 `uname -s = HarmonyOS` | 比 libvhdi 20251119（config 文件 2024-07-27 起）更老，`ohos` 三元组与 HarmonyOS 主机均在其知识范围外 | 配方显式传 `--build/--host=aarch64-unknown-linux-gnu`（rlog 1.4 同口径）；并以 `patches/0001-config-config.guess.patch` 让 `config.guess` 在 HarmonyOS 上直接回显同三元组，使干净构建门禁的裸 `./configure` 也能确定 build type。补丁只含主机探测逻辑，无平台宏 |
| 2 | Autoconf 临时目录 `Permission denied` | HMDFS 不保存 other 位，configure 内 `umask 077` 落盘目录不可写 | 构建期把 `configure` 的 `umask 077` 改成 `022`，全程 `umask 022` |
| 3 | 直接执行源码树脚本失败 | HMDFS 禁止直接 exec 源码树脚本 | `CONFIG_SHELL` 显式解释 `configure`；`make check` 传 `LOG_COMPILER` |
| 4 | runner 报 `Invalid test executable`（libtool 包装脚本） | `check_PROGRAMS` 产物是 libtool 包装脚本，真实 ELF 在 `.libs/` | 构建期给 `test_runner.sh` 加 `.libs/<name>` 解析并注入 `LD_LIBRARY_PATH`（两处 needle 计数守卫，布局变化即报错） |
| 5 | conan-verify 干净轮 `configure: error: working directory cannot be determined`（getcwd: Not supported） | hnp bash 5.3 的 getcwd 探测在部分 HMDFS 目录下随机失败（toybox `pwd` 同目录正常）；autoconf configure 对 `pwd` 失败硬退出。注意仅把 configure 以 `/bin/sh` 启动并不够：Conan self.run 会先 source 聚合的 conanbuild.sh，其中按 profile buildenv **重新导出** `CONFIG_SHELL=/data/service/hnp/bin/bash`（覆盖进程级钉定），autoconf/libtool 的早期 shell 检查按 `$CONFIG_SHELL` 起 bash | configure 阶段以 `/bin/sh` 启动并以**命令前缀赋值** `CONFIG_SHELL=/bin/sh`（source 之后生效、必然获胜），使 configure 及其子 shell 全程走 toybox ash；`make check` 的 runner 脚本需要 bash（113 处 `local`、ash 语法不兼容），保留 `LOG_COMPILER=$CONFIG_SHELL`（实证多轮正常执行） |

## 上游测试三步法（R51）

**清点**（静态事实，来源 `tests/Makefile.am`）：

- `check_PROGRAMS` 注册 **6** 个 C 测试程序：
  `fcrypto_test_blowfish_context` / `fcrypto_test_des3_context` /
  `fcrypto_test_rc4_context` / `fcrypto_test_serpent_context` /
  `fcrypto_test_error` / `fcrypto_test_support`
  （`fcrypto_test_memory.c` 是被多个程序包含的辅助源文件，不是程序）；
- automake `TESTS` 注册 **1** 个 shell runner：`test_library.sh`
  （`test_python_module.sh` 仅在 `HAVE_PYTHON_TESTS` 时加入，本配方
  `--disable-python`；`test_manpage.sh` 只在 `check_SCRIPTS`，不被
  `make check` 执行）。

**实跑**：在干净轮 `conan create` 的 `build()` 内 `make -j1 check` 执行；
结果数字以本轮 W3 日志为准，回填于 manifest.yaml `tests:` 小节与
test-report（不在此预填）。

**口径**：N = 上游注册的 6 个测试程序（check_PROGRAMS），runner 级
`test_library.sh` 单列；消费者测试（test_package）按模板表格单独计数，
鸿蒙专项断言计入"鸿蒙特有测试"行。

## 消费者测试（test_package）

- `test_libfcrypto.c`（通用，15 断言）：版本查询、RC4 上下文生命周期、
  公开测试向量（key "Secret"/明文 "Attack at dawn" → 45 A0 1F 64 5F C3 5B
  38 35 52 54 4B 9B F5，48 位密钥）、第二上下文解密回环、NULL 上下文错误
  路径（error 置位/打印/释放）；
- `test_ohos.c`（鸿蒙特有，7 断言）：`__OHOS__` 编译目标、打包共享库在
  OHOS 上的真实计算（RC4 向量）、可写临时目录（TMPDIR 优先、可写 /tmp
  兜底；只读 /tmp 且无 TMPDIR 时按 SKIP 记录、不计为通过）、临时文件
  建/写/重开/读回/删除生命周期。

## 知识增量评估（路径 B 未申报）

| 本轮可迁移做法 | 知识库既有条目 | 结论 |
|---|---|---|
| HMDFS umask 077→022、CONFIG_SHELL 执行、libtool `.libs` 测试适配 | `E007`/`E011`/`E087`/`E330`（同 libvhdi 口径） | 已收录 |
| 老版 config.guess/config.sub 不识别 HarmonyOS/ohos，回退 gnu 三元组 | rlog 1.4 已交付同方案（0001-config-config.guess.patch 先例） | 高度重叠 |
| libyal 发布包闭包审计 | `DRAFT-libfsntfs-release-archive-closure` | 重复 |

因此本 PR 不携带 `knowledge/drafts/**` 草稿，标题按任务来源取 `【积分赛】`。

## 验证记录

- 上游测试（check_PROGRAMS 6 程序，经 test_library.sh/test_runner.sh 逐程序
  执行）：6/6 PASS；runner 级 automake 汇总 TOTAL 1 / PASS 1 / SKIP 0 /
  FAIL 0。逐程序证据：`tests/test_library.sh.log`（Testing: blowfish_context/
  des3_context/error/rc4_context/serpent_context/support 各 PASS），原件哈希
  见任务目录 evidence。
- 消费者测试（test_package，确定性计数：每条断言恰好打印一行 PASS/FAIL 且
  程序以失败数非零退出）：通用 15 断言 + 鸿蒙专项 7 断言 = 22；预期
  22/22（100%），以本轮验证日志与退出码为准。
- 首轮验证（2026-09-18 07:46）：构建、上游测试全部通过；消费者测试因
  `libfcrypto_rc4_context_set_key` 的 24 位密钥低于 RC4 最小 40 位校验
  （`key_bit_size < 40` 即报错返回 -1）未通过，密钥上下文未初始化导致密文
  向量断言失败、回环碰巧一致。修正为 48 位密钥公开向量。
- 二轮验证（2026-09-18 08:0x）：W3 本地 CI 模拟全部通过（上游 6/6 +
  消费者 21 断言）；conan-verify 干净轮 configure 被 hnp bash getcwd
  随机失败拦截（见问题 #5），configure 改 `/bin/sh` 后重新验证。
- 三轮验证：conan-verify 干净轮在 source() 阶段被 github.com 连接超时拦截
  （设备网络间歇性；W3 因预下载走 curl 未受影响），源码改 pin 字节相同的
  Debian orig 镜像后重新验证。

## 遗留风险与未运行项

- pyfcrypto Python 绑定未构建、未测试（显式关闭，上游默认即关闭）；
- `test_manpage.sh`（man 页面检查）不在上游 `make check` 分母
  （仅 check_SCRIPTS），未运行；
- ossfuzz 目标未构建（上游默认关闭）。
