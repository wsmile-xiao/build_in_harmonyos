# argyll-cms 3.5.0 适配笔记

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | 上游自研 **Jam**（`jam -fJambase`，Perforce Jam + ArgyllCMS Jambase 1.3.3 规则集） |
| 编译日期 | 2026-09-27 |
| 编译器 | clang 15.0.4（OHOS SDK，默认 target `aarch64-unknown-linux-ohos`），GNU ar 2.45 |
| 目标平台 | HarmonyOS PC / OpenHarmony aarch64（musl libc） |
| 状态 | built（`conan create` 通过；conan-verify PASS；test_package 8+14 断言全绿） |
| 上游构建工具 | `tool_requires jam/ajam-2.5.2-1.3.4`（FT-Jam 2.5.2 + ArgyllCMS V1.3.3 Jambase） |

## 源码与版本核验

| 项 | 值 |
|---|---|
| 官方发布页 | https://www.argyllcms.com/downloadsrc.html |
| 官方源码 | https://www.argyllcms.com/Argyll_V3.5.0_src.zip |
| SHA256 | `f8576ce5589fd15620abb73ff049ea31f55ddbd1bba6d1ffa87452658e7bc85f` |
| 大小 | 15352322 字节 |
| 上游版本 | 3.5.0（ReadMe: "Version 3.5.0 ... bug fix update to V3.4.1"，2026-02-04） |
| 顶层结构 | `Jamfile` / `Jambase` / `Jamtop` / `JamExtra`(钩子) / `blddirs` `adirs` `afiles` 等 Jam 清单 |

## 依赖（W0：全部经 `conan download ... -r=ohpcd --only-recipe` 核验）

`Jamtop` 给所有 GUI 程序链接的 `GUILINKFLAGS`：

```
-L$(LibWinD) -lX11 -lXext -lXxf86vm -lXinerama -lXrandr -lXau -lXdmcp -lXss
```

| 依赖包 | 上游版本 | 来源 |
|---|---|---|
| libx11/6.4.0 | libX11-1.8.10 | GUILINKFLAGS `-lX11` |
| libxext/6.4.0 | libXext-1.3.6 | `-lXext` |
| libxxf86vm/1.1.5 | libXxf86vm 1.1.5 | `-lXxf86vm` |
| libxinerama/1.1.6 | libXinerama 1.1.6 | `-lXinerama` |
| libxrandr/1.5.5.1 | libXrandr 1.5.5 | `-lXrandr`（dispwin 的 XRR 显示管理） |
| libxscrnsaver/1.2.5 | libXScrnSaver 1.2.5 | `-lXss` |
| libxau/1.0.11 | libXau 1.0.11 | `-lXau`（与 libxcb/1.16 的约束一致） |
| libxdmcp/1.1.5 | libXdmcp 1.1.5 | `-lXdmcp`（libxcb/1.16 传递依赖同版本） |
| jam/ajam-2.5.2-1.3.4 | FT-Jam 2.5.2 | `tool_requires`（Argyll 专用 jam） |

传递依赖（由上面 8 个包引入，无需显式声明）：libxcb/1.16、libxrender/0.9.12、xorgproto/2025.1、xtrans/1.6.0。

> **libxrender/0.9.12 说明**：其 recipe 钉 `libx11/1.8.13`，而 libxrandr/1.5.5.1 强制整个图走
> cmd-pkgs 的 `libx11/6.4.0` 轨道，因此制品仓没有与该 config 匹配的 **binary**
> （recipe 已发布，`conan download --only-recipe` 通过，R36 门禁满足）。
> CI 的 `conan create ... --build=missing` 会为其从源码构建（本地实测可成功，约 20 秒）。
> 这是本包唯一的“无匹配 binary”依赖，`conan list` 无法判断（R35），已如实记录。

内部依赖（**不引入外部包**，用发布包自带源码）：

| 内置库 | 处理 |
|---|---|
| zlib / libjpeg / libpng / libtiff | 强制 `BUILTIN_Z/JPEG/PNG/TIFF=true`，用 Argyll 自带的源码树编译 |
| OpenSSL | 强制 `BUILTIN_SSL=true`，用自带的 `ccast/axTLS` |
| libusb | **不需要**：`spectro/usbio_lx.c` 直接使用 `<linux/usbdevice_fs.h>` + `ioctl`，OHOS sysroot 已提供该头文件 |

## 构建步骤（真实命令）

```bash
# 1) 取源码（配方 source()：conan get() 解压 Argyll_V3.5.0_src.zip）
# 2) 打补丁（apply_conandata_patches，7 个 patch，见下）
# 3) 生成 JamExtra（配方 generate()）：CC/C++ 取自 tools.build:compiler_executables，
#    X11HDRDIR/X11LIBDIR 取自依赖 cpp_info，BUILTIN_*=true，-I/-L/-rpath/-ffile-prefix-map
# 4) 构建 + 安装
jam -fJambase -j48          # ← 实际 -jN 由 tools.build:jobs / cpu_count 决定（实测 -j8）
jam -fJambase install       # → <src>/bin（48 个工具）+ <src>/ref（96 个参考数据文件）
# 5) 打包：bin/ + ref/ + licenses/License*.txt
```

`jam install` 的目标目录是 `$(DESTDIR)$(PREFIX)`，Jamtop 的默认 `DESTDIR` 就是工程根目录，
所以安装落在 `<source>/bin`、`<source>/ref`（与上游 `makeinstall.sh` 行为一致）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Unable to locate the X11 include files`（Jamtop EXIT） | Jamtop 只在 `/usr/X11R6`、`/usr/include`、`/usr/local/include` 等 FHS 固定路径 GLOB 查找 X11 头/库 | 补丁 `0001-Jamtop.patch`：让 Jamtop 优先接受 `X11HDRDIR`/`X11LIBDIR` jam 变量（回落到原 GLOB）；配方用上游自带的 `JamExtra` 钩子注入 Conan 依赖路径 |
| 2 | `jpeg/config.guess: unable to guess system type` + `configure: error: cannot guess build type` | 发布包内置的 jpeg(2011)/tiff(2008) `config.guess` 不认识 `uname -s = HarmonyOS`（E007） | 补丁 `0002`/`0005`（config.guess）：加 `*:HarmonyOS:*:*` 分支并输出 `aarch64-unknown-linux-ohos`；**并补 `echo "$GUESS" ; exit ;;`**——这两个老版本的 case 分支没有 echo/exit，只赋值不会生效 |
| 3 | `config.sub: Invalid configuration` | 老 `config.sub` 的 OS 列表没有 `linux-ohos`/`ohos` | 补丁 `0003`/`0006`（config.sub）：在 `maybe_os` 列表与 “MUST END IN *” 列表各加 `linux-ohos*`/`-linux-ohos*` |
| 4 | `config.status: error: could not setup config files machinery` / `can't create ./confXXXXXX/subs1.awk: Permission denied` | 内置 `configure` 用 `umask 077` 建私有临时目录，HMDFS 的 UID 映射让 0700 目录对当前进程不可写（E011） | 补丁 `0004`/`0007`（configure）：`umask 077` → `umask 022` |
| 5 | 首次构建 `llvm-ar: error: unknown option n` 等（34 个 target 失败，所有静态库归档失败） | **设备环境导出了通用工具链变量** `AR=llvm-ar`、`RANLIB=llvm-ranlib`、`NM/STRIP/AS/LD=llvm-*`，jam 会把同名环境变量导入为 jam 变量，于是 `AR ?= ar rusc` 被覆盖成 `llvm-ar`，归档命令失去操作符 `rusc` | 配方 `build()` 中剔除 `AR/RANLIB/NM/STRIP/AS/LD/CFLAGS/CXXFLAGS/CPPFLAGS/LDFLAGS`，并在 JamExtra 里显式 `AR = ar rusc ;` |
| 6 | 共享用户前缀污染 | 同上，环境里的 `CPPFLAGS=-I$HOME/usr/local/include`、`LDFLAGS=-L$HOME/usr/local/lib` 会被 Jambase 的 `CCFLAGS/LINKFLAGS ?=` 收编（R49/E524 风险） | 同 #5，构建前剔除这些变量；依赖路径一律由 JamExtra 显式注入 |
| 7 | 制品里出现构建机源码绝对路径 | Argyll 的错误宏把 `__FILE__` 写进 `.rodata` | JamExtra 追加 `-ffile-prefix-map=<src>=.`（实测泄漏字符串由 2 处降为 0） |
| 8 | `-ldl -lrt` 在 OHOS 是否可用 | Jambase 的通用 UNIX 分支固定加 `-ldl -lrt` | OHOS sysroot 提供 `libdl.a`/`librt.a` 空壳，链接正常，无需改动 |

## 源码修改（补丁清单，均在 `patches/`，由 `refresh-patch --auto` 生成）

| 补丁 | 文件 | 内容 | 平台宏 |
|---|---|---|---|
| `0001-Jamtop.patch` | `Jamtop` | X11 头/库搜索路径支持 `X11HDRDIR`/`X11LIBDIR` 覆盖 | 无 |
| `0002-jpeg-config.guess.patch` | `jpeg/config.guess` | 加 `*:HarmonyOS:*:*` 分支（含 `echo`/`exit`） | 无 |
| `0003-jpeg-config.sub.patch` | `jpeg/config.sub` | `linux-ohos*` 三元组 | 无 |
| `0004-jpeg-configure.patch` | `jpeg/configure` | `umask 077` → `umask 022` | 无 |
| `0005-tiff-config-config.guess.patch` | `tiff/config/config.guess` | 同上（HarmonyOS 分支） | 无 |
| `0006-tiff-config-config.sub.patch` | `tiff/config/config.sub` | 同上（`linux-ohos*`） | 无 |
| `0007-tiff-configure.patch` | `tiff/configure` | 同上（`umask 022`） | 无 |

> 七个补丁都不含 `__OHOS__` 之类的平台宏注入；`Jamtop` 的改动是**通用化**（把硬编码 FHS 路径改为可覆盖变量），
> 不是平台特判。内置 jpeg/tiff 的 `config.guess`/`config.sub`/`configure` 属于发布包自带的
> 构建脚本（非功能源码），改动仅为平台识别与临时目录权限。

## 上游测试入口核验（R51 第一步）

ArgyllCMS **没有统一自动化测试入口**，清点证据：

```bash
# 顶层 Makefile 只有 all / clean / install
$ cat Makefile
all::      jam -q -fJambase -j 3
clean::    jam -fJambase clean
install::  jam -q -fJambase -j 3 install

# Jambase 的伪目标里没有 check/test
$ grep -n "NotFile" Jambase
1193:NotFile all first shell files lib exe obj dirs clean install uninstall ;

# 发布包无顶层 tests/ 或 test/ 目录；无 ctest/pytest 注册
$ ls -d */test* 2>/dev/null     # 只有 tiff/test（内置 libtiff 自带，属第三方）
$ grep -rln "testing" doc/      # 只有与“色彩测试图表”相关的业务文档，无测试流程文档
```

上游实际可用的是散布在各子目录里的**自检/回归程序**（jam 默认目标就产出它们），
本次逐项真机执行，结果见 `reports/test-report.md`。

## 验证结果

```bash
# conan create（与 CI 同参）
conan create archives/a/argyll-cms/3.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="argyll-cms/*"
# → 构建成功；test_package 8/8 + 14/14 断言通过（日志 reports/conan-create.log）

# 配方验证
python3 scripts/ohc-run.py conan-verify argyll-cms 3.5.0
# → PASS：G1/G2/G3/G4 + L2/L4/L5（报告 reports/conan-verify-report.md）
```

产物：`bin/` 48 个命令行工具（dispcal/dispwin/dispread/colprof/colverify/targen/chartread/
cctiff/iccdump/icclu/iccgamut/collink/viewgam/...）+ `ref/` 96 个上游参考数据文件。

## 已知限制

- **R40 适配完整性说明**：本包属「图形渲染 / 外设」领域（X11 GUI 显示校准 + USB 光谱仪），
  适配改动全部是**构建期平台适配**（X11 路径注入、HarmonyOS 三元组、HMDFS umask），
  **没有**做 stub/`return 0` 之类的功能裁剪，也没有屏蔽任何代码路径：
  - GUI 工具（dispwin/dispcal/viewgam/…）真实动态链接 8 个 Conan X11 库，
    `test_ohos.sh` 断言 9/10/11 覆盖 NEEDED 集与运行期加载（含无显示服务时优雅报错）；
  - USB 仪器代码路径完整编译（`spectro/usbio_lx.c` + `<linux/usbdevice_fs.h>`），
    但**无对应硬件**，其真实仪器通信未在真机上验证——需人工确认（R40）。
  - 色彩引擎与文件格式部分（icclu/iccgamut/targen/iccdump 等）由 test_package 的 8 条功能断言
    在真机上以真实数据验证。
- **CI L2 冒烟测试会 skip**：Argyll 的全部 48 个工具都以非零码拒绝 `--version`/`--help`（用法用 `-?` 打印；
  `dispwin --version` 会先打印版本横幅 `Version 3.5.0` 再报 `Diagnostic: Unknown flag` 并以 1 退出），实测 0/48 返回 0，
  CI 的 L2（逐个 bin 尝试 `--version`/`--help`，非阻塞）因此没有可命中的二进制；
  真实功能验证由 `test_package/test.sh`（8 条断言）与 `test_ohos.sh`（14 条断言）覆盖。
- **GUI 工具需要 X 显示服务**：无显示时 `dispwin` 报 `Unable to open the default display` 并以 1 退出
  （已作为断言 11 固化）。
- 上游 `tdhsx` / `icctest` 两个自检程序自身报告失败（-O0/-O2/-fsigned-char 结果一致，与本平台适配无关），
  详见 `reports/test-report.md`。
---

**编译结束**: 2026-09-27 10:43
**最终状态**: built
