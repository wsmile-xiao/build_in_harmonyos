# libemf 1.0.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15.0.4（OHOS SDK，目标 aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

设备原生探索（任务私有目录 `ws/tmp/libemf-1.0.14`，源码树 `builds/libemf-1.0.14.work`）：

```sh
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config/config.guess config/config.sub
# 补 config.sub 第三处（见"遇到的问题"#2）
./configure --prefix=$HOME/usr/local
make -j2
make check
```

补丁固化：在 orig/work 双轨树上用 `ohc-run.py refresh-patch --auto libemf 1.0.14`
生成 3 个补丁（config.guess / config.sub / configure），随后由 finish 的
conan create 从干净源码复现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config/config.guess: unable to guess system type` | 2022 版 config.guess 不认识 `uname -s` 返回的 HarmonyOS（E007） | patch-autotools-ohos.pl 加入 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos` |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.sub 缺 ohos 支持，且 patch 脚本只做了 2/3 处修改（E072） | 手工补齐 kernel-OS 白名单 `\| linux-ohos*`，随后 config.sub 验证通过 |
| 3 | `config.status: error: could not setup config files machinery`（`can't create ./confXXXXXX/subs1.awk: Permission denied`） | configure 用 `umask 077` 建 config.status 临时目录，HMDFS 强制 setgid → 0700 目录连属主也不可写（E011/E129） | configure 内两处 `umask 077` → `umask 022`，随补丁固化 |
| 4 | 语言预检（R47）判 `detected_language=mixed`（nodejs 74/82 文件） | 统计把 `doc/doxygen-doc/html/` 里预生成的 doxygen 搜索索引 JS 当作主体源码 | 保存反证（doc/ 外 0 个 .js；真实代码 7×.c + 1×.cpp + 14×.h；构建系统 autotools）后按真实路径继续，详见 lang-preflight-override.md；未伪造 detected_language |
| 5 | init-build 把归档骨架写进了共享主检出 | `find_project_dir()` 从脚本位置（主检出）向上找 SKILL.md，与 cwd 无关 | 精确删除误写文件，后续所有 ohc-run 调用显式传 `--project-dir`/`OHC_PROJECT_DIR=<任务 worktree>`；主检出恢复原状 |

## 源码修改

三处均为 portability 补丁（`patches/`，由 refresh-patch --auto 生成）：

1. `0001-config-config.guess.patch` — 增加 HarmonyOS uname 分支，
   输出 `aarch64-unknown-linux-ohos`（+11 行）。
2. `0002-config-config.sub.patch` — ohos 三元组三处修改：
   `basic_os=linux-ohos` 映射、OS 白名单 `ohos*`、
   kernel-OS 白名单 `linux-ohos*`（+6/-2 行）。
3. `0003-configure.patch` — config.status 临时目录 `umask 077 → 022`（2 处）。

补丁均为纯构建配置修改，不含 `__OHOS__` 平台宏、不改动 `libemf/`、`src/`、
`include/`、`tests/` 任何源码或测试。

## 依赖版本

无外部依赖（仅 libc/libc++/pthread；configure 的 ceil/floor 探测判定不需要
显式 -lm，pthread 由系统提供）。

## 验证结果

```sh
# 设备原生（探索轮）
$ ./configure --prefix=$HOME/usr/local   # exit 0
$ make -j2                               # exit 0
$ make check
  PASS: docheck1.sh  PASS: docheck2.sh  PASS: docheck3.sh
  # TOTAL: 3  PASS: 3  SKIP: 0  FAIL: 0  ERROR: 0
# 未注册的 3 个上游程序（同轮构建后显式运行）：
$ ./check4 && ./example1 && ./example2 example1.emf
  check4 rc=0  example1 rc=0  example2 rc=0   # 产出 check4.emf/example1.emf/example2.emf
# 6 个上游测试程序全部运行成功（3 个注册测试 3/3 PASS + 3 个未注册程序 rc=0）
```

上游测试清点（tests/Makefile.am）：`TESTS = docheck1.sh docheck2.sh docheck3.sh`
（分别运行 check1/check2/check3 并与 `tests/emfs/*.emf` 做 `cmp -l` 逐字节比较）；
`check_PROGRAMS = check1 check2 check3 check4 example1 example2` 共 6 个程序，
其中 check4/example1/example2 上游未注册。适配后上游测试文件未做任何修改；
配方在 `make check` 之后显式运行未注册的三个（`./check4 && ./example1 &&
./example2 example1.emf`），六者实测全部返回 0 并各自产出元文件
（证据：`logs/*-six-programs/output.txt`）。

正式轮（finish 内嵌 W3 conan create + test_package）见 reports/ 与任务证据。

## 交付物

| 文件 | 说明 |
|------|------|
| `libEMF.so.1.0.0`（`libEMF.so`、`libEMF.so.1` 符号链接） | 生成 EMF 的 C 库（libtool -version-info 1:0:0） |
| `include/libEMF/emf.h` + `include/libEMF/wine/*.h` | 公共 C API 与 GDI 类型头 |
| `bin/printemf` | 元文件读取工具（commands.json 声明，R38） |
| `libEMF.la` | libtool 归档描述（共享库元数据，随包安装；G4 报告 lib/ 为 0 个 .a + 3 个 .so） |
| `libEMF.a` | 仅在 `-o libemf/*:shared=False` 时产出：配方在该选项下向 configure 追加 `--enable-static --disable-shared` |
| `licenses/COPYING`、`licenses/COPYING.LIB` | 上游 GPL-2.0 / LGPL-2.1 文本 |

## 注意事项

- 库主体（libemf.cpp / emf.h）为 LGPL-2.1-or-later；`printemf`（src/printemf.c）
  为 GPL-2.0-or-later，包内同时包含两级许可文本，`license` 字段按库主体填
  LGPL-2.1-or-later。
- `printemf` 只有在 `./configure --enable-editing` 时才会打印元文件内容；
  默认配置下它只做可读性校验（可读 rc=0 / 不可读 rc=1），本配方保持上游默认。
- `make check` 需要写出 `check*.emf` 并在 tests/ 内运行，`make distclean` 会清理
  这些产物；探索轮在生成补丁前先 distclean，避免把测试输出误收进补丁。

## 测试包布局与上游接口注意事项

- `test_package/` 故意使用 Conan 默认布局（`self.folders.generators = "."`，CMake 消费者建在
  `build/`）而不是 `cmake_layout()`：平台 smoke-test 门禁以
  `<archive>/test_package/conanrun.sh` 作为运行环境脚本来执行包内 `bin/printemf`，
  使用 cmake_layout 时该脚本会落到 `test_package/build/<配置>/generators/` 而门禁找不到。
  随之落地的 CMakeDeps/CMakeToolchain 生成文件由同目录 `.gitignore` 排除。
- 消费者测试按上游 1.0.14 源码与设备探针（`logs/…-api-semantics/`）显式断言的接口语义：
  `GetDesktopWindow`/`GetDC` 返回文档化的哑值 0（无图形系统要求）；
  `SetPixel` 返回哑值 `RGB(0,0,0)`（不是错误码）；`SetTextColor` 返回**前一次**颜色；
  `DeleteEnhMetaFile` 必须早于 `DeleteDC`（两者取自同一句柄表）；
  `GetEnhMetaFileHeader` 会把库内部 header 对象 memcpy 给调用方，因此只断言调用契约
  （返回字节数），不比较字段内容——该行为属上游缺陷，全平台一致，不因适配引入。
