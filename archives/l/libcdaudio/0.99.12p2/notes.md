# libcdaudio 0.99.12p2 适配笔记

## 编译环境

- 构建系统: autotools（dist 自带预生成 `configure`，GNU Autoconf **2.59** / 2005；单一 configure，无 AC_CONFIG_SUBDIRS）
- 平台任务: contrib-13086（libcdaudio 0.99.12p2），claimer Ember5843
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建
- 编译器: clang/clang++ 15.0.4
- 依赖: 无
- 上游: 项目主页即 SourceForge（https://libcdaudio.sourceforge.net/），SourceForge 是其唯一官方发布点
- 源码 sha256: `5fdaf9af5ac4f75c0215d000b82b128fd054a582f81cc4f039a1e7fe69335ebb`
- 状态: built（G0/G1/G2/G3 全过，test_package 20/20）

## 源码面貌（摸底结论）

- 主体 **C**：`src/` 下 10 个 `.c` + 3 个 `.h`，单目录结构
- 交付形态：静态库 `libcdaudio.a` + 安装头 `include/cdaudio.h`
  （`cdaudioname` 在非 BeOS/非 Irix 主机上保持 `cdaudio`，故链接名是 `-lcdaudio`、头名是 `cdaudio.h`）
- 可选特性：`--enable-threads`（默认 guessed）、`--enable-xbox-fix`（默认 no）；无外部依赖
- 上游**无测试套件**：所有 `Makefile.am` 均无 `TESTS`/`check_PROGRAMS`/`noinst_PROGRAMS` 测试声明，
  tarball 内无 `*test*` 源文件，configure 期也不注册测试
- 与硬件无关、可测的核心逻辑：`cdaudio_getversion` / `cd_version`、LBA↔frame 换算
  （150 frame 前导区）、MSF↔frame 换算（75 frame/秒）、`cd_init_device` 的错误路径

## 编译步骤（设备实机）

```sh
cd $HOME/build_in_harmonyos
python3 scripts/ohc-run.py conan-verify libcdaudio 0.99.12p2 --project-dir "$PWD"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Invalid configuration 'aarch64-unknown-linux-musl': machine 'aarch64-unknown-linux' not recognized` → `configure: error: ./config.sub aarch64-unknown-linux-musl failed` | 本 dist 的 `config.sub` 是 **2005-04-25** 版，`aarch64` 这个 cpu 名 2012 年才加入 config.sub，`musl` 这个 os 名 2011 年才加入——沿用 libcaca 的 `aarch64-…-musl` / `aarch64-…-gnu` 对会被直接拒绝 | 改用该版本能接受、且仍能构成"build≠host"的三元组对：`--build=arm-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`。该版本 config.sub 对**带 `unknown` 厂商的四段名**是原样放行的（实测 `aarch64-unknown-linux-gnu` 通过、`aarch64-linux-gnu` 被拒），而本代码库的 `configure.ac` 只按 `host_os` 分支 beos/irix/solaris，不看 build_cpu，因此这个替代是无副作用的 |
| 2 | 断言 `cd_init_device("/dev/null")` 应返回描述符，实测返回负值（唯一失败项） | 我按"open 会成功"推断，但该函数在 `open` **之前**先做挂载表探测（`setmntent(MOUNTED)`）；设备上挂载表不可用，于是它提前拒绝了 /dev/null | 断言改为描述**性质**而非实现路径：`cd_init_device()/cd_stat()` 绝不允许把可打开但非 CD 的节点报告为可用 CD 接口。两种实现路径（提前拒绝 / 发放描述符但 cd_stat 失败）都满足该性质——这是更稳的写法，也避免了把某平台的实现细节固化成期望 |
| 3 | CI 报 `configure: error: C compiler cannot create executables`（设备上同一配方通过） | conan 的 `AutotoolsToolchain` 会把 `CC=/data/service/hnp/bin/clang` 写进 `conanautotoolstoolchain.sh`，但该脚本**只被 conan 自己的 `Autotools()` 助手 source**，配方用裸 subprocess 跑 configure 时 conan 不把 build env 写进 `os.environ`（libcaca 那轮已发现同类现象）。CC 未设 → autoconf 退到 PATH 里的裸 `clang`：设备 PATH 含 `/data/service/hnp/bin` 故恰好命中 hnp 工具链，而 CI worker 的 PATH（`/data/app/bin:/system/bin:...`）不含，命中的 clang 没有 OHOS sysroot，链接 conftest 失败 | `_build_environment()` 里从 profile 的 `tools.build:compiler_executables` 显式导出 `CC`/`CXX`（也符合 R33：工具链来自明确声明而非 PATH） |
| 4 | 老 autoconf 的 shell 兼容性 | 本包 configure 由 autoconf 2.59 生成，**不含** `exec 7<&0`（实测 0 处），所以 toybox sh 的 fd 限制在这里不成立 | 仍统一使用平台 profile 声明的 `/data/service/hnp/bin/bash`：automake 的 `all-recursive` 用 `for subdir in $list` 依赖 POSIX 词分割，zsh 不做该分割（libcaca 实测踩过），bash 同时满足两类要求，行为可预测 |

## 源码修改

无补丁，未改动上游任何源码。

## 依赖版本

无外部依赖（这是本包的一个优势：不引入任何依赖链）。

## 验证结果（设备实机实测，2026-09-14）

```text
✅   G0: PASS
✅   G1: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: libcdaudio 0.99.12p2
```

消费者测试（test_package，ctest + 直接执行）：

```text
ok 1 - cdaudio_getversion() equals the header's LIBCDAUDIO_VERSION
ok 2 - version encodes major 0, minor 99, micro 12
ok 3 - cd_version() writes the package name at the start of the buffer
ok 4 - cd_version() NUL-terminates a short buffer (no overflow)
ok 5 - cd_lba_to_frames(0) == 150
ok 6 - cd_lba_to_frames(1000) == 1150
ok 7 - cd_frames_to_lba(150) == 0
ok 8 - cd_frames_to_lba(1000) == 850
ok 9 - cd_frames_to_lba() clamps frames below the lead-in to 0
ok 10 - cd_msf_to_frames(00:00:00) == 0
ok 11 - cd_msf_to_frames(00:01:00) == 75
ok 12 - cd_msf_to_frames(01:00:00) == 4500
ok 13 - cd_msf_to_frames(01:02:03) == 4653
ok 14 - cd_frames_to_msf(4653) yields 01:02:03
ok 15 - cd_lba_to_msf(0) yields 00:02:00
ok 16 - cd_msf_to_lba(00:02:00) == 0 (guard boundary)
ok 17 - cd_msf_to_lba(00:02:01) == 1
ok 18 - cd_lba_to_msf()/cd_msf_to_lba() round-trip exactly
ok 19 - cd_init_device() on a missing device node fails with a negative value
ok 20 - an openable non-CD node is never reported as a usable CD interface
1..20
# 20 checks, 0 failures
```

## 可复用要点

沿用本仓既有做法：自实现 `_fetch()`（显式 CA 兜底 + 重试 + `.part` 原子改名 + sha256 校验）、
设备 job 首行 `mkdir` 互斥锁、`conan remove` 清缓存残留、tar 用 `COPYFILE_DISABLE=1`。
本包新增的可复用经验记于 `manifest.yaml` 的 `knowledge_gained`，其一是**老 autotools 的
config.sub 与 aarch64/musl 的兼容套路**（2005 版 config.sub 不认 aarch64，用带 `unknown`
厂商的四段名绕过），对竞赛池里大量 2012 年前的老包直接适用。
