# vkeybd 0.1.18d 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure/CMake）
- 编译日期: 2026-09-29（run 178 于 2026-09-30 复跑设备确认，同一配方同一结果）
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- Conan: 2.29.1，profile `ohos-aarch64`（os=OHOS/arch=armv8/libc++）
- 设备: 3QC0124C11000071
- 状态: built

## 编译步骤

上游是 2007 年代码的手写 Makefile 工程，产出两个二进制：

- `vkeybd` —— Tcl/Tk GUI，往 sequencer 后端发 MIDI 事件
- `sftovkb` —— 纯 C 的 SoundFont(SF2) → vkeybd 预设列表转换器

全部适配都是**命令行 make 变量覆盖**，上游源码零改动：

```sh
make -C <source_folder> vkeybd sftovkb \
  'COPTFLAGS=-O2 -fPIC -Wall -I<各依赖 includedirs>' \
  'TCLLIB=-ltcl9.0' 'TKLIB=-ltcl9tk9.0' \
  'TCLINC=' 'TKINC=' 'XLIB=-lX11' 'XINC=' \
  'USE_AWE=0' 'USE_MIDI=0' 'USE_ALSA=1' 'USE_LASH=0' \
  'EXTRALIB=-lasound -ldl' \
  'LDFLAGS=-L<tcl/lib> -L<tk/lib> -L<x11/lib> -L<alsa/lib>' \
  'VKBLIB_DIR=<package_folder>/share/vkeybd'
```

设备实测编译链（日志 `job_vkeybd_create.log`）：

```
clang ... -DVKB_USE_ALSA -c -o vkb.o vkb.c      # AWE/MIDI 确实被 USE_*=0 排除
clang -L...tcl -L...tk -L...x11 -L...alsa -o vkeybd \
      vkb.o vkb_device.o oper_alsa.o -ltcl9tk9.0 -ltcl9.0 -lX11 -lasound -ldl -lm
clang ... -o sftovkb sftovkb.o sffile.o malloc.o fskip.o -lm
package(): Packaged 6 files
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ohc-run.py init-build` 下载失败「下载内容是 HTML」 | 该子命令拉的是仓库首页而非 tag tarball | 改用 codeload：`https://codeload.github.com/tiwai/vkeybd/tar.gz/refs/tags/v0.1.18d`，sha256=`df5dece0e18db3ac17222faa537e9b450d6ab0044792be194077d669d46d4b45` |
| 2 | conandata 按版本嵌套时 `get()` 报 `unexpected keyword '0.1.18d'` | `**conan_data["sources"]` 把版本号当成了 get() 的关键字参数 | 改扁平 `sources:` + 显式 `filename:`（codeload URL 无 `.tar.gz` 后缀，缺 filename 会被 get() 误判为 zip 报 BadZipFile） |
| 3 | `make: invalid option -- /` | make 变量赋值未加引号，`COPTFLAGS=-O2 -fPIC -I/a` 被 shell 词分割成多个 make 选项 | 每个赋值都过 `shlex.quote()` |
| 4 | make 在 `src/` 里，Conan 在 build root 执行 | `basic_layout(src_folder="src")` | 命令写成 `make -C <source_folder> ...` |
| 5 | 设备 conan 下载报 `CERTIFICATE_VERIFY_FAILED`（curl/urllib 却正常） | 设备无常规 CA：`/etc/ssl/certs` 与 `~/.conan2/cacert.pem` 全缺 | 装 harmonybrew 的 `cert.pem` 到 `~/.conan2/cacert.pem` 并导出 `REQUESTS_CA_BUNDLE`。**属环境缺口，非配方缺陷**（§1.2 CA 兜底要求） |
| 6 | `CREATE_RC=1`，test_package 报 `sftovkb/vkeybd not on PATH` | `VirtualRunEnv` 只导出**依赖**的 bin/lib，不含被测包自身 `bindirs`（设备 grep 实证：包里唯一出现的 `vkeyb8...` 只在 `VKEYBD_DATADIR`，PATH 里没有） | test_package 里显式 `Environment().prepend_path("PATH", bindirs)`，同时 `define("LD_LIBRARY_PATH", "")` 清掉环境自带的，使库解析断言有意义 |
| 7 | 原测试脚本在 vkeybd 缺失时仍报 PASS | `command -v` 通过不代表可执行，后续调用 exit=127 被宽松断言放过 | 改为 `[ -x "$path" ]` + 显式拒绝 rc=127 + 拒绝空输出 |

## 源码修改

无。零 patch，上游源码一字未改；所有适配都在 make 命令行变量层。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| tcl | 9.0.3.2 | 制品仓**无 8.6 可与 tk 配对**；Makefile 写死 `TCL_VERSION=8.4` |
| tk | 9.0.3.2 | 制品仓仅 9.0.3.1/9.0.3.2，**无 8.6 系列**；tcl/tk 主版本必须一致 |
| libx11 | 6.4.0 | 提供 Xlib 与 `X11/` 头；上游要的 `/usr/X11R6` 前缀在 OHOS 不存在 |
| alsa-lib | 1.2.16 | 唯一保留的 MIDI 后端 |

传递依赖（实测解析）：`xorgproto/2025.1 + libxau/1.0.11 + libxdmcp/1.1.5 + xtrans/1.6.0 + libxcb/1.16`。

## 验证结果

设备 `conan create`（`job_vkeybd_create.log`，2026-09-29 19:18）：

```
CREATE_RC=0
PASS: sftovkb converts a real SF2 into the expected preset list
PASS: sftovkb sanitises preset names ([] -> (), {} -> space)
PASS: sftovkb rejects a non-SoundFont input with a non-zero exit
PASS: sftovkb prints usage when called without arguments
PASS: vkeybd runtime data files are installed
PASS: vkeybd starts, loads its libraries, and reaches its own output (exit=1, headless)
ALL_VKEYBD_TESTS_PASSED
```

`sftovkb` 是端到端实跑：脚本先用 python3 生成结构合法的 SF2（38 字节 phdr / 22 字节 inst / 46 字节 shdr，3 个具名预设 + 终止 EOP），再断言它输出的三行 preset 列表与名称消毒器行为（`[` → `(`、`{` → 空格）。`vkeybd` 是 Tcl/Tk GUI，无头设备开不了窗口，故通过两个可观测的非 GUI 面验证：安装的数据文件，以及一次真实调用必须动态解析 `libtcl9tk9.0`/`libX11`/`libasound` 并走到自己的参数处理（headless 下退出码非零是预期的；exit=127 或 loader error 才算失败）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/vkeybd` | X11/Tk 虚拟 MIDI 键盘 |
| `bin/sftovkb` | SoundFont → vkeybd 预设列表转换器 |
| `share/vkeybd/{vkeybd.tcl,vkeybd.list,vkeybdmap,vkeybdmap-{de,es,fr}}` | 运行期数据；`VKBLIB_DIR` 在编译期就指向此目录 |

## 注意事项

- **`TKINC`/`TCLINC`/`XINC` 留空是有意的**：`-I` 全部并入 `COPTFLAGS`。若单独设 `TCLINC`，Makefile 拼 CFLAGS 的方式会丢掉 `-DVKB_TCLFILE`/`-DVKBLIB_DIR`/`-DVKB_USE_ALSA` 这几个它自己加的 define。
- **同样不要覆盖 `CFLAGS`**：Makefile 在 CFLAGS 内部追加上述 define，覆盖它等于同时丢掉它们。
- **tcl/tk 锁 9.0.3.2 这一对**是硬约束，不要单独升其中一个；混用主版本会链接失败。
- 已发布 tcl/tk 的 soname 是 `tcl9.0`/`tcl9tk9.0`，不是 Makefile 写死的 `-ltcl8.4`/`-ltk8.4`；改版本号时 `TCLLIB`/`TKLIB` 要跟着改。
- `VKBLIB_DIR` 必须是**绝对路径**且指向本包的 `share/vkeybd`——vkeybd 启动时用它定位自己的 Tcl 脚本，指错就会去源码树找。
- AWE/MIDI 后端 `#include <linux/soundcard.h>`（Linux OSS ioctl 接口，OHOS 无此头），是不可移植的，已关掉。这是**声明式降级**，不是静默丢弃，见下节。
- `commands.json` 在软件级 `archives/v/vkeybd/commands.json`（`ref=vkeybd/0.1.18d`, `type=tool`），**不要**挪进版本目录，那会违反 PF8/R38。

## 降级边界声明

- **AWE / MIDI 后端关闭**：`oper_awe.c` / `oper_midi.c` 依赖 Linux OSS 的 `<linux/soundcard.h>`（`SNDCTL_*` ioctl 族）。OHOS 无此头，且该接口是 Linux 内核 ABI、非 POSIX，移植它等于重新实现一层内核接口，收益为零。保留的 ALSA 后端是上游自带的现代替代路径，功能等价（MIDI 事件 → sequencer）。
- **`USE_LASH=0`**：lash 是 X11 会话启动脚本，本包不含会话管理，不需要。
- 上游无测试套件（tag 树实测：无 `tests/`、无 `make check`、无 CI 配置，仓库最后提交 2016-01-20），故按 R51 如实声明零上游用例，测试全在 test_package 的真实消费路径上。

## 发现与知识

- ✅ **`VirtualRunEnv` 不含被测包自身 `bindirs`**（E691 同族但非同一条）：`generators = "VirtualRunEnv"` 生成的 `conanrunenv-*.sh` 只导出**依赖**的 bin/lib。设备 grep 实证：本包目录 `vkeyb8...` 在整个 env 文件里唯一的出现处是 `VKEYBD_DATADIR`（data 路径），PATH 中没有它。CLI 包的 test_package 必须自己补 `Environment().prepend_path("PATH", bindirs)`。E691 讲的是「static 包 bindirs 为空」，本条是「bindirs 非空但仍不进 conanrun PATH」，两者需分开记。
- ✅ **CLI 测试里 `command -v` 通过 ≠ 可执行**：vkeybd 缺失时 `command -v` 仍可命中 PATH 上的同名残留（或 shell 报出一个跑不动的名字），后续调用 exit=127 却被宽松断言放过。断言必须落在「`[ -x "$path" ]` + 显式拒绝 rc=127 + 拒绝空输出」三层上。
- ✅ **无头设备上验证 X11/Tk GUI 二进制**：不要求开窗口，改为断言（a）编译期路径（`VKBLIB_DIR`）真的烤进了二进制字符串，（b）一次真实调用能动态解析 `libtcl9tk9.0`/`libX11`/`libasound` 并走到自己的参数处理。headless 下退出码非零是预期结果，exit=127 或 `error while loading shared libraries` 才是失败。
- ✅ **make 变量赋值必须整体加引号**：`make 'COPTFLAGS=-O2 -fPIC -I/a'` vs `make COPTFLAGS=-O2 -fPIC -I/a`，后者被 shell 词分割后 make 把 `-fPIC`/`-I/a` 当成自己的选项，报 `make: invalid option -- /`。配方里统一用 `shlex.quote("{name}={value}")`。
- ⏳ 待提取：Makefile 在 CFLAGS 内部自行 `-DVKB_TCLFILE/-DVKBLIB_DIR/-DVKB_USE_ALSA`，故**不能覆盖 CFLAGS**，只能覆盖它的组成项（COPTFLAGS）。这是一类可复用模式：上游 Makefile 自拼 define 时，配方应覆盖"被拼进去的变量"而非"被拼出来的变量"。
- ⏳ 待提取：codeload URL（`.../tar.gz/refs/tags/<tag>`）无 `.tar.gz` 后缀时，`conan.tools.files.get()` 会误判 zip 报 `BadZipFile`，必须显式给 `filename:`。

---

**编译结束**: 2026-09-29 19:18
**最终状态**: built
