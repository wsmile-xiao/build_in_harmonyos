# simstring 1.0 适配笔记

## 编译环境

- 构建系统: autotools（发行包自带 autoconf 2.6x 生成的 configure，2010-03）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18，`/data/service/hnp/bin/`）
- 状态: built（设备真实构建 + Conan 验证通过；合并前不标 published，见 AGENTS §1 O5）

## 编译步骤

```sh
# 配方驱动（conan create 内部）与设备手工探索同序：
./configure --prefix=<prefix>     # 三元组 aarch64-unknown-linux-ohos（补丁后 config.guess 自判，未传 --build/--host）
make -j1                          # 全绿（约 20 个 TU：frontend/sample + 头文件）
make install DESTDIR=<staging>    # bin/simstring + include/simstring/*.h + share/doc/simstring/
make check                        # rc=0，但每个子目录 "Nothing to be done for 'check'"——上游无测试套件
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 发行包 bundle 的 config.guess/config.sub 时间戳 2009-04-27：CPU 表无 aarch64、OS 表无 HarmonyOS/linux-ohos；`uname -s` = HarmonyOS | 补丁 0001/0002（对老基线手写，语义 = 官方 `patch-autotools-ohos.pl` 对现代基线的产出；官方脚本在老基线只成功一半 cg=1/sub=0/rc=1）。**未用 `--build/--host`**（E007 禁止：会翻成 cross_compiling=yes 跳过 AC_RUN_IFELSE） |
| 2 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | autoconf 内置 `umask 077 && mktemp -d "./confXXXXXX"`；设备目录落盘属主恒映射为共享 uid 20001006（进程 euid=20020085），mode 0700 丢 group-w 后无任何写路径（toybox `mktemp -d` 权限随 umask 敏感：077 拒 / 022 通 / 002 通） | 补丁 0003：configure 两处 `umask 077` → `umask 022`（config.status 由 configure 内嵌模板生成，一处双修；a52dec `0002-configure-umask-022.patch` 同形）。E110/E125 的"换构建目录"建议在同文件系统下无效 |
| 3 | `memory_mapped_file_posix.h:128: error: invalid use of non-static data member 'read'`（write 同） | 上游 1.0 的 `simstring.h` 未包含 `<unistd.h>`，POSIX `read/write` 声明不可见、被类成员名遮蔽 | 补丁 0004：加 `#include <unistd.h>`（= Debian 官方补丁 `0001-To-use-standard-library-correctly.patch`，上游 master 同样以 6209ea8 修过） |
| 4 | 手工 `./configure` 报 `no acceptable C compiler found in $PATH` | 设备/worker PATH 无 `cc`/`gcc`（只有 clang/clang++），init-build 预检已告警 | 配方走 Conan `AutotoolsToolchain`：profile `ci/conan/profiles/ohos-aarch64` 经 `tools.build:compiler_executables` 注入 CC/CXX，手工探索时显式 `CC=clang CXX=clang++` |
| 5 | 设备 harmonybrew 有 automake/autoconf，CI worker 无（假绿风险） | notes/device-facts.md §一.4 | 本包**不跑 autoreconf**：全部改动落在发行包自带 configure/config.guess/config.sub 的补丁上，设备与 worker 同源同 diff，不依赖 harmonybrew |
| 6 | 采信轮连续 2 轮 G2 `sha256 hash failed`（Provided 386f5e18… / Computed fa0fa296…） | chokkan.org 对 `.tar.gz` **无条件**加 `Content-Encoding: gzip`/`x-gzip`（4 形态实测：A-E=gzip→gzip，identity/bogus/缺省→x-gzip，body 恒 233446B 原文件字节）；Conan 的 `requests.Session`+urllib3 透明解码一层 → 拿到内层 plain tar（1187840B，sha=fa0fa296），与 conandata 记录的**文件面** sha（386f5e18 = 官方 dist == Debian .dsc PGP == `curl -O`，五次复核）必然不一致 | 按 blepvco 0.1.0 先例：`source()` 先 `get()`、捕 `ConanException` 后 **urllib 回退**（urllib 不做 Content-Encoding 解码 = 文件面原始字节）+ `check_sha256` 兜底校验 386f5e18 + strip_root unzip；**conandata sha 保持 386f5e18 不动**（bsdgames-nonfree 2.17 的"改记解码后 sha"变体只适用于双 gzip 无法取原始字节的场景，且会让 W4 独立复算（curl 文件面）判 mismatch）。双面 sha 复现：`curl -O <url> && sha256sum` → 386f5e18；`gunzip -c <该文件> \| sha256sum` → fa0fa296 |
| 7 | round4：test.sh 五查全 `rc=127`（`simstring: command not found`） | 本包 `package_type="header-library"` ⇒ conan `VirtualRunEnv` 对该 requires 边 `run=False`（`tools/env/virtualrunenv.py:79` `if require.run:`），`cpp_info.bindirs` 永不写入 conanrun——生成的 `conanrunenv-*.sh` 变量表为空（`for v in` 空列表，source 后 `command -v simstring` NOT FOUND 实证）；打包二进制实物在且直跑 `-v` rc=0（装载健康） | 按 abiword-plugin-* 族先例：`test()` 取 `self.dependencies["simstring"].package_folder/bin` 作 `$1` 显式传入 test.sh、脚本用 `"$BIN_DIR/simstring"` 调用（MANIFEST 同步）。方案 B（改 `package_type="application"` 使 `run=True` 走 PATH，aa3d 先例）被裁决否决——头文件库标 application 属表意失真、影响面溢出本任务 |

## 源码修改

- `patches/0001-config.guess.patch` — 主 case 首分支前插 HarmonyOS 分支，输出 `aarch64-unknown-linux-ohos`
- `patches/0002-config.sub.patch` — maybe_os 组合表 +`linux-ohos*`、CPU 表 +`aarch64`、os 字段表 +`-linux-ohos*`
- `patches/0003-configure.patch` — 临时目录 idiom `umask 077` → `umask 022`（2 处）
- `patches/0004-include-simstring-simstring.h.patch` — `#include <unistd.h>`（Debian 同款）

无平台宏（`__OHOS__`）注入，无 `--build/--host`，无镜像/搬运源。

## 依赖版本

- 硬依赖: **无**（`requirements()` 为空）。configure 仅 `AC_CHECK_HEADERS(stdint.h sys/mman.h)` + `AC_CHECK_LIB(m, sqrt)` + mmap 探测，全部由 OHOS sysroot/libc 提供；Debian Build-Depends 也只有 `debhelper-compat (= 13)`
- 构建期: 自带 autotools 产物（无需 autoreconf/automake），clang 15 + make

## 验证结果

```bash
# 源码双面 sha256 复现（Content-Encoding: x-gzip 双面）
curl -O https://www.chokkan.org/software/dist/simstring-1.0.tar.gz && sha256sum simstring-1.0.tar.gz
#   → 386f5e18c9a92a84eccd6caee407e28da939dd74bb68bd17912c4d918f0e4171（文件面，conandata 记录值）
gunzip -c simstring-1.0.tar.gz | sha256sum
#   → fa0fa2969ec5be85e5752156c469ffef07fb90f4780e77d2a57beb1ccf34cdb0（HTTP 解码面 = Conan requests 栈实收字节）
# 原生（设备）
sh ./configure --prefix=...   → rc=0, checking build system type... aarch64-unknown-linux-ohos
make -j4                      → rc=0
make install DESTDIR=...      → rc=0（bin/simstring + include/simstring/*.h + share/doc）
make check                    → rc=0（上游无测试：Nothing to be done for 'check'）
# 冒烟（设备真实运行）
simstring -v                  → "SimString 1.0 Copyright ..."  rc=0
printf 'apple\napplication\nbanana\n' | simstring -b -d words.db  → Number of strings: 3
printf 'apple\n' | simstring -d words.db -s exact -t 1.0 -q       → 	apple
./sample                      → 命中 Barack Hussein Obama II（头文件 API 端到端）
# test_package（conan create 内）
test_simstring（C++ 消费者） → 12 assertions OK
test.sh（CLI 五查）           → ALL CLI CHECKS PASSED (5/5)
```

上游测试统计与清点见 `test_package/MANIFEST.yml`（N=0，清点命令在注释内）与
`reports/test-report.md`（仓库外留档，不进 PR）。

## 注意事项

- 本包含 CLI（`bin/simstring`）+ 头文件库：软件级 `commands.json`（type=tool）与
  `cpp_info.bindirs = ["bin"]` 成对出现（PF8/L0k 口径）；`cpp_info.libs = []`
  （头文件库，不链接任何 simstring 库产物）。
- `cdbpp.h` 使用已废弃的 `std::binary_function`：clang 15 下仅 `-Wdeprecated-declarations`
  警告，不影响构建与运行（未改动上游语义）。
- 上游 1.0 无测试套件（N=0）：通过率分母用 test_package 自写断言（17 = 12 + 5），
  鸿蒙特有测试行见 PR 正文统计表。
