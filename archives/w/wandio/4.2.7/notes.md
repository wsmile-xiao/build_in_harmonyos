# wandio 4.2.7 适配纪要

> 适配时间: 2026-09-25
> 申请人: gcw_uQ09W7jl
> 队伍: 干
> 状态: built（工作树已完成，待 HMBS 真机预检回填证据后提交）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | wandio |
| 版本 | 4.2.7（首次适配，无后缀） |
| 构建系统 | 直接编译（custom，不走 autotools；详见 §二） |
| 源码 | https://github.com/LibtraceTeam/wandio/archive/refs/tags/4.2.7-1.tar.gz |
| 校验 | sha256 45021795b5c4d1609ba509358e730ea605c4c9621704d75214abb003f37602ab（Homebrew 公式同源交叉确认） |
| 上游测试 | 无 automake TESTS（Makefile.am/SUBDIRS 审计见 MANIFEST；另有独立 wandiocat 打包脚本，见 §四） |

## 二、构建配置（为什么不用 autotools）

- GitHub tag 包只有 `configure.ac`/`Makefile.am`、无生成的 `configure`。
- 在真机构建沙箱现场 bootstrap 不可行，已实证两轮失败：
  1. 直接 `autotools.configure()` → `.../b/configure: not found`（Error 127）；
  2. `tool_requires` automake+libtool 后跑 `autoreconf -fi` →
     `autoreconf: not found`（`autoreconf` 本体在 autoconf 包内）；
  3. 补齐 autoconf/2.72 后，传递依赖 m4/1.4.19 需从源码构建，
     其 configure 重 exec `$CONFIG_SHELL`（`/data/service/hnp/bin/bash`），
     该路径在构建沙箱内不存在 → m4 构建 Error 127。
     m4 是配方目录外的第三方包，无法在本 PR 内修复。
- 因此仿 cbm/0.4-1（“Direct compilation bypassing autotools”）直接编译：
  源文件集合与 `lib/Makefile.am` 关闭全部可选后端时完全一致
  （wandio.c、ior-peek.c、ior-stdio.c、ior-thread.c、iow-stdio.c、
  iow-thread.c），另编 `tools/wandiocat/wcat.c` 得 `wandiocat`。
- `build()` 在构建目录生成最小 `config.h`（全部 `HAVE_LIB*`/
  `HAVE_HTTP`/`HAVE_SYS_PRCTL_H` 置 0，WANDIO 4.2.7 版本宏），
  语义等价于上游
  `./configure --without-bzip2 --without-zlib --without-lzo --without-lzma --without-zstd --without-lz4 --without-qatzip --without-http`：
  wandio.c 的条件分支全部退化到 stdio 直通（压缩输入报明确错误，
  压缩输出回落 stdio 并告警），零外部依赖。
- 编译器/归档器以 Conan 配置为首选（R33），但构建沙箱内 profile 的
  `/data/service/hnp/bin/clang` 曾报 `inaccessible or not found`
 （Error 127，2026-09-25 预检）：`build()` 先按
  conf → `$CC`/`$AR` → HMBS 工具前缀
  `/storage/Users/currentUser/usr/local/bin` → PATH 裸名
  （clang/clang-15/cc/gcc、llvm-ar/ar）→ OHOS SDK llvm 通配路径的顺序
  逐个 `isfile` 预过滤并实际执行 `--version` 探活，首个可用者胜出；
  全部失败才回退 conf 原值以保留原始报错。`self.run` 统一走
  `env="conanbuild"`，调用点对工具路径加双引号；test_package 的
  `build()` 同样探活后以 `-DCMAKE_C_COMPILER=<可用编译器>` 覆盖
  CMakeToolchain 的默认值，避免测试消费者配置阶段复现同一 Error 127。
- 产物：`lib/libwandio.a`（shared=True 时为 .so）、`include/wandio.h`、
  `bin/wandiocat`、`licenses/COPYING*`。

## 三、依赖与补丁情况

| # | 依赖 | 结论 | 备注 |
|---|------|------|------|
| 1 | （无） | 零依赖 | 可选后端全部关闭，无需 conan download 预检；构建期亦无 tool_requires |

- 源码零修改，无 patches/。

## 四、测试接入

- 上游 automake 口径确无 TESTS：`upstream_tests_exist: false`，`upstream_test_total: 0`，
  口径 `autotools_tests`，五项审计来源见 test_package/MANIFEST.yml。
  另如实审计 `test/do-basic-tests.sh`：它是独立于 `make check` 的 wandiocat
  打包验证脚本（7 读 + 7 写），每个压缩用例都要求对应可选后端与外部压缩
  工具，本零依赖最小构建不适用，故未接入。
- 新增 `test_package/test_wandio.c`（4 个用例，20 个断言）：
  1. `test_lookup`：gzip/zstd 解析与未知方法返回 NULL（压缩类型表与后端
     开关无关，上游 wandio.c 静态表）；
  2. `test_detect`：`.gz`/`.zst`/纯文本后缀识别；
  3. `test_roundtrip`：`wandio_wcreate` 写入后 `wandio_create` 读回比对；
  4. `test_text_api`：`wandio_printf`/`fgets`/`peek`/`tell`/`seek` 联动（`tell` 按上游 `peek_tell` 语义断言 peek 前后稳定，而非绝对 0，见 test_wandio.c 注释）。
- `test_package/conanfile.py` 不再走 CMake（CMakeToolchain 把 profile 的
  坏编译器绝对路径硬编码进 `conan_toolchain.cmake`，`-D` 覆盖不生效，
  configure 仍以 Error 1 失败）：改为与主包同路的直接编译，
  用探活后的编译器把单文件 `test_wandio.c` 对已打包的
  `libwandio.a/.so` 直编为 `build_folder/test_wandio`，`test()` 复用
  shell 存在性校验后直调；`CMakeLists.txt` 保留仅供审计，不参与构建。
- 双标记由测试二进制统一打印，计数同源（`tests_run/tests_failed`）：
  上游 `no_tests`（0/0），新增 `discovered=4`。

## 五、验证情况

```bash
# 本轮为工作树准备轮，未在本机运行 conan（规范要求真机验证）。
# 待 HMBS 后台同步代码树并在 HarmonyOS aarch64 真机执行：
#   conan create archives/w/wandio/4.2.7 -pr:h=ci/conan/profiles/ohos-aarch64 ...
# 回填 conan create 日志中的执行数/通过数后，再由 HMBS 提交并建 PR。
```

## 六、注意事项

- Windows 检出注意：上游 main 含 `archives/g/gama/2.29` 下带回车文件名，
  本机用 non-cone sparse 排除该目录后同步；远端 Linux 真机不受影响。
- 后续如需压缩后端，可按 `zlib/1.3.1`、`zstd`、`lz4` 已发布版本逐个
  `requires` 并把对应 `io*-*.c` 加入源文件表、翻转 `config.h` 开关，
  另起 `4.2.7.N` 后缀版本。
- `wcat.c` 依赖 `<err.h>`（OHOS musl 与 glibc 均提供；bionic 缺失，
  但本配方仅支持 Linux/OHOS）。
