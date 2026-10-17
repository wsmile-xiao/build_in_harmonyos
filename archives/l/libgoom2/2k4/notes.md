# libgoom2 2k4 适配笔记

## 编译环境
- 构建系统: autotools（上游自带 configure，2005-02-07 冻结的 2k4-0 发行包）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS SDK native，`/data/service/hnp/bin/clang`，Target: aarch64-unknown-linux-ohos）
- 状态: built

## 软件与构建范围

goom2k4 是音频可视化效果库（XMMS goom 插件的 2004 重写版）。包内提供：

- `src/libgoom2`：可视化效果共享库（本次适配目标，Makefile.am 的 SOURCES 共 24 个编译单元：
  22 个手写 C 源文件 + 上游预生成的扫描器 goomsl_yacc.y/goomsl_lex.l）
- `xmms-goom/`：XMMS 可视化插件（需要 XMMS2 开发包）
- `sdl-goom/`：SDL/GTK 独立演示程序（需要 SDL 与 GTK）

后两者由上游 configure 的 `HAVE_XMMS`/`HAVE_SDL` 条件自动关闭（设备与 CI 均无
XMMS2/SDL 开发包），实际构建产物只有共享库、头文件与 pkg-config 文件。

## 编译步骤

1. `conan create` 由配方驱动：`get()` 下载 SourceForge 官方源码
   （`goom-2k4-0-src.tar.gz`，sha256 校验）→ `apply_conandata_patches()` 应用三个补丁 →
   `_compiler_env()` 从 profile `tools.build:compiler_executables` 注入 `CC/CXX/AR/RANLIB` →
   `CONFIG_SHELL=/bin/sh SHELL=/bin/sh ./configure --prefix=<package_folder>` →
   `make -j2` → `make -j1 check`（结构性空跑，留档）→ `make install`。
2. configure 不传 `--build/--host`：三元组补丁让 config.guess 直接认出
   `aarch64-unknown-linux-ohos`，构建是原生编译（非交叉），`AC_RUN_IFELSE` 类检查正常执行。
3. 上游 tarball 自带生成好的 `goomsl_yacc.c`/`goomsl_lex.c`，且时间戳与 `.y`/`.l` 相同，
   make 不会触发 bison/flex 重新生成（设备有 flex/bison，CI worker 不需要它们）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one`，config.guess 打印 uname 信息后退出 1（回退分支还报 `can't create .../cgiicNNNf/dummy.c: Permission denied`） | 2004-09-07 版 config.guess 不认识 `uname -s = HarmonyOS` | 补丁 `patches/0001`：在 `arm*:Linux:*:*)` 前插入 `*:HarmonyOS:*:*` 分支，按 UNAME_MACHINE 输出 aarch64/arm/x86_64/i686-unknown-linux-ohos（旧式脚本用 echo+exit，不能套用新版补丁脚本的 `GUESS=` 锚点，参见知识草稿 DRAFT-E564） |
| 2 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`（3 段形态同样被拒） | 2004 版 config.sub 的 maybe_os 列表无 `linux-ohos*`、OS 白名单无 `-linux-ohos*`，且 CPU 列表没有 aarch64/arm64 | 补丁 `patches/0002`：三处锚点（maybe_os 列表、basic OS 列表、CPU 列表）都补齐；验收判据为 `config.sub "$(config.guess)"` 原样往返 `aarch64-unknown-linux-ohos` |
| 3 | configure 退出码 0，但 Makefile 全部没生成、`make` 报 `No targets specified and no makefile found`；configure 日志里 `./config.status[618]: can't create ./confstatXXXXXX/subs.frag: Permission denied` | HMDFS 上 `umask 077 && mktemp -d` 创建的临时目录对当前进程不可写（设备事实 §10 / E011，tslib 1.22 同款） | 补丁 `patches/0003`：configure 内两处 `umask 077` → `umask 022`（mktemp 主路径与 `mkdir ./confstat$$-$RANDOM` 回退路径） |
| 4 | 进入配方阶段后 configure 探测 `aarch64-unknown-linux-ohos-gcc/gcc/cc` 全部落空 | OHOS 适配版 conan 不把 `tools.build:compiler_executables` 映射为 CC/CXX | `_compiler_env()` 运行期注入 `CC/CXX/AR/RANLIB`（adplay/1.9、jack/1.9.22、tslib/1.22 先例） |
| 5 | 构建日志出现 `make: jobserver mkfifo ...: Operation not permitted` | 设备/SELinux 拒绝创建 FIFO；GNU make 自动退化为 pipe jobserver | 噪声，不处理（设备事实 §13：并发未退化） |

## 上游测试清点（R51 三步法）

- **清点**：`grep -rn "TESTS\|check_PROGRAMS" --include="Makefile.am" --include="configure.in" .`
  零命中；`test/` 只有 17 行的 `testapp.c` 手工演示程序且没有 `Makefile.am`
  （不参与任何构建目标）；`tools/` 下是 gfont/minicompress 代码生成器。
  → 上游自动化测试入口 0 个。
- **运行**：`make -j1 check` 在根、src、xmms-goom、sdl-goom 四个目录全部输出
  `Nothing to be done for 'check'`（结构性空跑），已留档在 W3 日志。
- **申报**：上游通过率 0/0（不适用），不据此省略消费者测试；消费者测试计入
  「鸿蒙特有测试」行。

## 源码修改

三个补丁均为 portability 性质，不含平台宏（`__OHOS__` 零出现）、不改业务逻辑：

- `patches/0001-config-guess-harmonyos-ohos.patch`：config.guess 新增 HarmonyOS 分支（+9 行）
- `patches/0002-config-sub-linux-ohos.patch`：config.sub 三处白名单（+3 行，各一行内改动）
- `patches/0003-configure-umask-022-for-hmdfs-temp-dirs.patch`：configure 两处 umask 077→022

## 依赖版本

- 无外部依赖（W0 确认：`conan install --requires=libgoom2/2k4 --build=never` 在
  ohpcd 未命中、依赖清单为空；`libc.so` 提供 pthread/math，`llvm-readelf -d` 显示
  共享库 NEEDED 仅 libc.so）。XMMS/SDL/GTK 是可选前端，不构建。

## 验证结果

探索性构建（设备 aarch64 真机，OHOS SDK native clang，与 CI 同源）：

```bash
sh config.guess                     # aarch64-unknown-linux-ohos
sh config.sub "$(sh config.guess)"  # aarch64-unknown-linux-ohos（原样往返）
sh config.sub aarch64-linux-ohos    # aarch64-unknown-linux-ohos（3 段形态同样接受）
./configure --prefix=$D/install      # 退出码 0（build/host system type 均为 aarch64-unknown-linux-ohos）
make -j2                            # 退出码 0（0 error，15 warning：GNU 指示符/format-security/abs(float)/void* 截断，均不影响构建）
make install                        # 退出码 0
```

产物清单：

- `lib/libgoom2.so.0.0.0`（SONAME `libgoom2.so.0`，+ `libgoom2.so.0`、`libgoom2.so` 符号链接）
- `include/goom/`：goom.h、goom_plugin_info.h、goom_typedefs.h、goom_graphic.h、
  goom_config_param.h、goom_visual_fx.h、goom_filters.h、goom_tools.h、goomsl.h、
  goomsl_hash.h、goomsl_heap.h、goom_config.h（12 个头文件）
- `lib/pkgconfig/libgoom2.pc`

真机运行（消费者测试，`-lgoom2` 链接后直接运行）：

```
ok: goom_init(320, 240) returns a plugin instance
ok: requested resolution is applied (320x240)
ok: screen.size equals width*height
ok: at least one visual FX is registered
ok: all 64 audio frames produced a framebuffer
ok: first sampled framebuffer is painted (non-zero hash)
ok: framebuffer changes across frames (animation is live)
ok: sound analysis consumed the audio frames (volume in (0,1])
ok: goom_set_resolution(640, 480) is applied
ok: goom_update keeps rendering after a resolution change
ok: resized framebuffer differs from the 320x240 frame
ok: goom_close completed without crashing
checks=12 failures=0
```

## 关于 L5 产物基线与 ELF 内嵌构建路径（2026-09-18 重验说明）

首次验证（HEAD 93f36ccf）时 conan-verify 的 L5 保存了产物基线
（`reports/baseline.json`，17 个文件）。随后只修改文档（notes.md、
test_package/MANIFEST.yml、reports/test-report.md）重新验证时，L5 报 4 个文件差异
（`lib/libgoom2.so`、`.so.0`、`.so.0.0.0`、`lib/pkgconfig/libgoom2.pc`）：

- `libgoom2.pc` 内嵌 configure 的 `--prefix=<本轮私有 CONAN_HOME 的包目录>`；
- `.so` 带 DWARF 段（`.debug_info` 等），其中编译目录/源码路径指向
  `<本轮私有 CONAN_HOME>/p/b/<包>/b/src`。

两者都随「每轮验证使用随机命名的私有 CONAN_HOME」变化，同源码、同补丁重验
必然产生字节差异，与制品质量无关（配方与补丁未变，G2/G3/G4/L2/L4 与消费者测试
结论不受影响）。按 conan-verify L5 提示（"同源码重验出现 .so 差异时可删除
reports/baseline.json 重立基线，语义等同首轮"）删除该基线并重新建立；
`reports/baseline.json` 属 .gitignore 覆盖的本地验证产物，不进入 PR。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgoom2.so.0.0.0 | ~423 KB | 音频可视化效果库（ABI libgoom2.so.0） |
| include/goom/*.h ×12 | — | 公共 API 头文件 |
| libgoom2.pc | 290 B | pkg-config 描述文件 |
