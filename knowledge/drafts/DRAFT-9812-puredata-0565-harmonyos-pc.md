# HarmonyOS PC 上 Autotools 构建依赖触发 HMDFS 临时目录失败的规避方法

> 草稿：`draft: true` · contributor_id：`iKalous_OscarP` · 来源任务 #9812 / PR #13882

## 错误特征

当上游只提供 `configure.ac`，配方通过 Conan `tool_requires` 获取 Autotools 时，依赖图可能找到 recipe 却没有 OHOS 匹配二进制，于是 Conan 在设备上从源码构建 m4 等 bootstrap 工具。m4 构建过程中可出现：

`config.status: error: could not setup config files machinery`

`./confXXXXXX/subs1.awk: Permission denied`

同一设备上 Harmonybrew profile 已提供 m4、autoconf、automake、libtoolize；但 Conan m4 的递归源码构建会先触发 HMDFS 临时目录权限故障。此时单纯改 Pure Data 自身的 TMPDIR 无法修复依赖 recipe 的 configure。

## 触发条件

- HarmonyOS PC / AArch64，构建环境使用 Harmonybrew profile。
- 上游源码没有生成后的 `configure`，需要 `autoreconf -fi`。
- Conan 对一个或多个 `tool_requires` 只能找到 recipe，无法找到当前 OHOS profile 的二进制包。
- 依赖包在 HMDFS 构建目录下运行 Autoconf，临时目录创建成功但后续文件写入被拒绝。

## 根因与实测对照

| 路径 | 实测结果 |
|---|---|
| Conan `m4/1.4.19` OHOS package 缺失后从源码构建 | 失败于 `config.status` 创建 `subs1.awk`：`Permission denied` |
| 使用 Harmonybrew profile PATH 中的 m4 1.4.21、autoconf 2.73、automake 1.18.1、libtoolize 2.6.2 | `autoreconf -fi` 成功 |
| 直接调用 configure、未生成 Conan Autotools toolchain | clang 未被映射成 CC，报告 `C compiler cannot create executables` |
| 生成 `AutotoolsToolchain`，并按 E205 补齐 config.guess/config.sub 的 HarmonyOS 识别 | Pure Data configure、编译、安装及 test_package 均通过 |

## 推荐方案

1. 先在目标 profile 的 PATH 中确认 `m4`、`autoconf`、`automake`、`libtoolize` 的来源与版本。Harmonybrew profile 已提供这些工具时，直接用该受控工具链执行 `autoreconf -fi`，避免为工具引入会在 HMDFS 上源码构建的 Conan 依赖。
2. 用 `AutotoolsToolchain(self).generate()` 生成编译环境；针对旧版 GNU config helpers，按 E205 用 `patch-autotools-ohos.pl` 更新 config.guess/config.sub，使设备原生检测返回 HarmonyOS triplet。不要仅为绕过无法识别 triplet 而强塞 `--build/--host`；同时确认 Conan 生成的 CC 指向 profile 中的 clang。
3. 对源码中的 HMDFS 临时目录权限问题，仍按实际日志给被测项目自身设置 build-local `TMPDIR` 并处理 configure umask。该措施不能替代解决依赖 package 的 HMDFS 失败。
4. 上游没有注册测试时，先核对测试注册项。Autotools 可能仍生成 `make check` 空目标；可以实跑并记录其退出码及零执行程序，但不能将 0/0 写成非空测试套件通过。另用 test_package 为公开程序/API 增加消费者验证。

## 禁止做法

- 不要假设 `tool_requires` recipe 存在就代表 OHOS 对应二进制也存在；先看 Conan 解析是否进入依赖源码构建。
- 不要把依赖 recipe 的 HMDFS 权限失败归因到被测库源码，也不要仅为继续流程关闭测试。
- 不要让原始 configure 调用绕开 profile compiler 映射。
- 不要用 `--build/--host` 代替修正不识别 OHOS 的 config.guess/config.sub（E205）。
- 不要把自动生成但未注册任何测试的 `make check` 目标写成存在上游测试；应记录实际注册数与执行情况。

## 与既有条目的边界

- E114 记录 Autoconf 临时目录在 HMDFS 上的权限异常；本条聚焦该异常发生在 Conan 的递归 build-tool package 中，以及何时改用 profile 已有工具。
- E060/E110/E112/E118/E125/E126/E175 记录 HMDFS 对 Autoconf 临时目录及其权限的限制；本条不主张新的 HMDFS 根因，只补充当该已知失败发生在 Conan 递归 build-tool package 中时，如何判别并切断依赖源码构建链。
- E205 要求修复 GNU config.guess/config.sub 对 OHOS triplet 的识别。本方案遵循其约束，明确禁止把 `--build/--host` 当作识别问题的绕过方式。
- E490 关注 Autotools helper 脚本执行位丢失；本条故障是 config.guess 能运行但因 HarmonyOS 识别失败及 HMDFS 的编译探测写入失败，两者触发阶段和修复点不同。
- E528 记录 OHOS 原生 Autotools 工具目录、编译器和 TMPDIR 的闭合；本条补充“缺少 OHOS build-tool 二进制导致依赖源码构建”的判别与规避，并要求用 AutotoolsToolchain 显式提供 CC。
- E533 覆盖 libarchive 的配置、依赖、权限和测试分类；本条只聚焦 Autotools bootstrap 依赖的 HMDFS 源码构建链。
- E407 覆盖 PortAudio 的 pthread_cancel 探测和无设备测试；Pure Data 复用该线程取消边界，本草稿不重复主张。本配方的取消路径即按 E407 用 `AC_CHECK_FUNCS([pthread_cancel])` 生成 `HAVE_PTHREAD_CANCEL` 门控，不引入平台条件编译宏。
- E460 主张把缺失的 bootstrap 工具**声明为 Conan `tool_requires`** 并锁定 gnulib 修订，以复现「tag 不含生成文件」的 Autotools 源码树；本条给出的是相反方向的判别：当 profile PATH 已提供这些工具、而 `tool_requires` 在 OHOS 只有 recipe 没有二进制时，声明它反而会把 HMDFS 临时目录故障引进依赖链。两者触发条件不同（E460 缺工具、本条是工具已在 profile 且工具包无法在 HMDFS 构建），选型时先看 `command -v`。
- E543 也使用 `tool_requires` 注入构建机缺失的工具（flex/bison），但因果链是交叉编译的 `AC_TRY_RUN` 与工具缺失，不涉及依赖包在 HMDFS 上的源码构建失败；本条针对的是「工具包本身构建失败」这一层。
- E486 处理 bootstrap 期宿主 ELF 首次执行前的签名；E510 处理 toybox `patch` 需前置 harmonybrew GNU patch；E509 处理 harmonybrew 二进制的 OpenSSL 3.x 符号依赖。三者都涉及宿主工具但都不涉及 `config.status` 在 HMDFS 临时目录的写入被拒，与本条不重叠。
- E468 记录 `PKG_CONFIG_PATH`/`ACLOCAL_PATH` 需经 `buildenv_info` 显式导出，并把需要 `.m4` 的工具声明为 `tool_requires`；其「m4」指 autoconf 宏目录，与本条的 GNU m4 工具包构建失败无关。
- E268/E122 记录 `patch-autotools-ohos.pl` 步骤 2.3 的守卫过宽，导致 config.sub 的 kernel-OS 校验列表可能不被补上。本条第 2 步要求按 E205 调用该脚本，故必须与之划界：本条**不主张**该脚本的守卫结论，只主张「先确认可用工具链来源、不要让 Conan 去源码构建 bootstrap 依赖」这一判别；守卫已在本次提交内按列表成员形式（`linux-ohos*`）收紧，且实测对 automake 1.18.1 自带 `config.sub`（timestamp 2024-05-27，其校验列表上游已含 `linux-ohos*-`）行为完全不变。

## 查重与独立验证

查重按 origin/main tip `2446216757be20359617ac140c2e103fac6398f0` 重测，`knowledge/graph/E[0-9]{3}.kv` 共 542 条正式条目。单个关键词**是有命中的**，本草稿不声称单关键词 0 命中：`subs1.awk`/`could not setup config files machinery` 命中 E011/E052/E110/E112/E114 等（HMDFS 临时目录权限族，本条不主张新根因）；`tool_requires` 命中 E220/E242/E359/E460/E468/E543；`Harmonybrew` 命中 E509/E510/E533；`pthread_cancel` 命中 E085/E127/E407/E513。

0 命中针对的是**这条因果链本身**——「`tool_requires` 只有 recipe、没有当前 build profile 的 OHOS 二进制 → Conan 转从源码构建该 bootstrap 依赖 → 该依赖自己的 `config.status` 在 HMDFS 临时目录写文件被拒 → 判别方法是先查 profile PATH 是否已有 m4/autoconf/automake/libtoolize」。按两两交集实测：`m4 ∩ config.status` = 0 条；`Harmonybrew ∩ tool_requires` = 0 条；`pa_linux_alsa.c` = 0 条。相邻的 E460/E543 结论方向与本条相反（主张声明 `tool_requires`），已在上一节逐条划界。

独立验证来自 Conan tool package `m4/1.4.19` 的上游构建：同一 HarmonyOS 设备和隔离 `CONAN_HOME` 下，它在 `config.status` 阶段重现 `subs1.awk: Permission denied`。之后 Pure Data 改为使用设备 profile 的 Harmonybrew bootstrap 工具链，并经 `AutotoolsToolchain` 生成器完成构建，test_package 5/5 通过。

## 可复现命令与结果

`CONAN_HOME=~/work/psj/ch-pd13882 conan create archives/p/puredata/0.56.5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`

结果：`CREATE_EXIT:0`；上游没有注册自动化测试（0 项）；消费者/平台测试 5/5 通过；ELF 为 AArch64，解释器是 `ld-musl-aarch64.so.1`。

## 来源

- 软件任务：puredata/0.56.5，任务 #9812。
- 知识议题：#3618。
- 证据 PR：#13882。
- 作者：iKalous_OscarP。
