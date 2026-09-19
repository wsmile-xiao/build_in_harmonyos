# Critical Mass 1.0.2 — 适配记录

> 上游: Critical Mass (Critter)，Frank Becker，SDL 1.2/OpenGL 太空射击
> 源码: SourceForge（官方 /download 对非浏览器 UA 返回 403/HTML 拦截或截断文件，已实测，
> 改用校验一致的 macports/gentoo 镜像下载，见 conandata.yml url 列表）
> sha256: 846db2d30d39e559612328594084a7aef980169948b2cfaee9fddec8ffdef724（5122126 字节，
> MD5 e2aff114bffa717fb79c82e1dc473ebe）
> 工程类型: autotools（automake 1.4 era）；configure 3583 行生成物，直接补丁生成物、不重跑 autogen；
> C++ SDL 1.2 游戏（bin_PROGRAMS=critter）

## 结论快照
- 产物: `bin/critter` 可执行文件。`package_type: application`，无库 / 无头文件。
- 上游自动化测试: **0**（无 test/ 目录、无 AC_CONFIG_TESTDIR/TESTS、configure.in 无 check_PROGRAMS）。
- 反空壳 / 功能冒烟（test_package）: `critter --version` → stdout 含 `Critical_Mass 1.0.2`。
  patches/0004 使 --version 在 SDL/GL 初始化前退出（无头环境可跑，无需显示/音频）。

## OHOS 关键适配（详见 conanfile.py）
1. **SDL 1.2 栈**：SDL 1.2 API 由 sdl12-compat/1.2.68 提供，SDL_image/SDL_mixer 用仓库
   sdl-image/1.2.12、sdl-mixer/1.2.12 配方。老栈无 pkg-config "sdl" 模块、依赖包无可用
   sdl-config → patches/0003 为 configure.in 增加 AC_ARG_VAR(SDL_CFLAGS, SDL_LIBS)，
   配方 generate() 显式传入（sdl-image 先例技法）。
2. **GL 动态解析**：configure.in 在 TARGET=UNIX 且非 dyngl 时 AC_CHECK_LIB(GL)，OHOS 无
   libGL.so → 必传 `--enable-dyngl`（DYNAMIC_GL 经 SDL_GL_GetProcAddress 运行时解析）。
3. **交叉模式**：双三元组 `--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
   强制 autoconf 交叉模式，跳过 conftest 运行探测（无签名 ELF 无法在 worker 沙箱运行）；
   同时避开 HMDFS 上 config.status mktemp(0700) 临时目录不可写问题（sdl-image/aalib 先例）。
4. **config.guess/config.sub**：2012 旧版不识别 aarch64-unknown-linux-ohos → 打包 FSF 2024
   版到 files/，build() 拷入源码根（cheops 先例）。
5. **捆绑 curl 移除**：上游 tarball 自带 2009 版 curl/ 子树（configure.in AC_CONFIG_SUBDIRS）。
   patches/0001 移除 curl/ 子树引用，改由 conan curl/8.15.0.1 满足 game/OnlineUpdate.cpp。
6. **libpng12 → png16**：patches/0002（OHOS 只有 png16，配置依赖 libpng/1.6.58）。
7. **data/ 直读**：resource.dat 由 tools/Packer 从 data/description_file 打包生成（pkgdata_DATA
   安装）。patches/0006 移除该生成链（game/Makefile.in 删 resource.dat 依赖），运行时改读
   $(pkgdatadir)/data（share/Critical_Mass/data/）；package() 手工拷贝 6 个数据子目录
   （bitmaps/models/sounds/levelpacks/paths/system）；music/lg-criti.xm 仍是 pkgdata_DATA。
8. **签名**：OHOS ELF 须 package() 内 llvm-objcopy --remove-section .codesign +
   binary-sign-tool sign -selfSign 1（julius 先例），否则 test_package 运行报
   Operation not permitted。
9. **-j1**：HMDFS 并行 mkfifo/jobserver 问题规避（julius/cheops 先例）。

## 源码修改（patches/0001-0011，均直接作用于生成物/官方源）

| 补丁 | 内容 | 说明 |
|------|------|------|
| 0001-remove-bundled-curl | 移除 curl/ 子树引用（顶层 Makefile.am SUBDIRS、configure.in AC_CONFIG_SUBDIRS、configure） | 改由 conan curl 制品满足 |
| 0002-png12-to-png16 | libpng12 → png16 的检查与链接名 | OHOS 只有 png16 |
| 0003-sdl-config-compat | configure.in 增加 AC_ARG_VAR(SDL_CFLAGS, SDL_LIBS)，SDL 检查用其覆盖 | 老栈无 pkg-config/sdl-config 可用 |
| 0004-headless-version-exit | main.cpp 在 SDL/GL 初始化前处理 --version（stdout 输出后 exit(0)） | 无头环境冒烟验证 |
| 0005-toolchain-cflags | 阻止 configure 重置 clang 工具链 CFLAGS/CXXFLAGS | 交叉工具链标志保护 |
| 0006-resource-data-dir | game/Makefile.in 移除 resource.dat 生成依赖；main.cpp fallback 绝对路径化直读 data/ | 跳过 Packer/resource.dat 链 |
| 0007-hashmap-explicit-using | libc++ hash_map 适配：hashMap.hpp 改 using-declaration；10 文件 `hash_map<const string,...>` 去冗余 const key；Input.hpp hash<Trigger> 特化搬入 std；FindHash.hpp 第二重载迭代器去 const | clang 15/libc++ 模板推导行为 |
| 0008-png16-write-api | utilssdl/PNG.cpp libpng 1.2 不透明成员访问 → 1.6 API（png_get_io_ptr/png_jmpbuf） | libpng 1.6.58 |
| 0009-makefile-includes-abs | 4 个 Makefile.in 子目录相对 include（-I../utils 等）→ $(top_srcdir) 绝对化 | conan VPATH build-release/ out-of-tree |
| 0010-packer-const-compare | Packer.cpp operator< 非 const 引用 → const 引用 | C++11 list::sort const 实参 |
| 0011-main-udl-zlib | main.cpp `__TIME__`/`__DATE__` UDL 宏化（BUILD_STAMP_）+ 显式 #include <zlib.h> | C++17 P0041R1；zlib 为直接依赖（zlibVersion()），conanfile 已显式 require |

补丁基线验证：0001-0005 在官方 tarball 解包上按序 dry-run 全部 OK；0006 在
"官方 tarball + 0001-0005" 上真实应用 OK，结果与探针工作区逐字节一致
（diff -rq 无差异）。0007-0011 在 2026-09-18 复核：pristine tarball 解包
依次应用 0001-0011 后与 "官方 tarball + 0001-0006" 基线再应用 0007-0011
逐字节一致（diff -rq 无差异），且 main.cpp 与编辑工作树一致。

## 依赖版本
- sdl12-compat/1.2.68（SDL 1.2 API 提供者）
- sdl-image/1.2.12（SDL_image）
- sdl-mixer/1.2.12（SDL_mixer）⚠️ 本地已构建成功（conan cache 有 OHOS aarch64 包），
  配方在 archives/s/sdl-mixer/1.2.12/；若 ohpcd 远端尚无该制品，CI L0i(R36) 会报
  unpublished_deps——属依赖交付缺口（非本库代码问题），需先发布 sdl-mixer 或
  本 PR 一并携带 sdl-mixer 配方。
- libpng/1.6.58（png16）
- curl/8.15.0.1（OnlineUpdate）
- zlib/1.3.1.1（直接依赖：main.cpp zlibVersion()；conanfile 显式 require）

## 验证结果
```bash
$ conan create archives/c/criticalmass/1.0.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --build="criticalmass/*"
```
2026-09-18 本地实测（日志 tmp/hk/conan-create-0011.log）：
- 依赖解析 10/10 全部命中本地缓存（sdl12-compat/sdl-image/sdl-mixer/libpng/
  libjpeg-turbo/libtiff/libwebp/zstd/curl/zlib）
- configure（交叉模式、--enable-dyngl、SDL_CFLAGS/SDL_LIBS 显式注入）全部依赖 yes
- make -j1 全部目标编译链接成功（tinyxml/utils/utilssdl/utilsgl/game/tools/Packer）
- package：bin/critter（817 KB AArch64 ELF，自签）、bin/Packer、
  share/Critical_Mass/data/{bitmaps,levelpacks,models,paths,sounds,system}、
  share/Critical_Mass/lg-criti.xm
- test_package：`[pass] critter --version prints 'Critical_Mass 1.0.2' (rc=0)`
- conan create 退出码 0

本地 CI 门禁（2026-09-18，ci/conan/build_and_test.sh，CI_PACKAGES=archives/c/criticalmass/1.0.2，JUNK_PR_DIFF 注入模拟 buildbot prdiff 模式）：
- L0_RESULT=pass: all checks passed（含 L0i 六依赖全部 in registry：sdl12-compat/sdl-image/sdl-mixer/libpng/curl/zlib；L0j 首发布无冲突；L0k commands.json 有效；L0m 目录结构有效；KC/JC prdiff 全过）
- L1_RESULT=pass: test_package executed（L1a/L1b/L1e 负向测试全过：test 真实依赖 criticalmass）
- L2_RESULT=skip: 非阻塞（沙箱无法执行 aarch64 OHOS ELF 做 smoke，CI worker 上真实执行）
- L4_RESULT=pass: patches clean（无危险函数）
- L5_RESULT=pass: bin/ has content
- Build Summary: Total 1 / Success 1 / Pass rate 100.0%
- 日志：tmp/hk/ci-run3.log、.ci_logs/conan_build_criticalmass_1.0.2.log

## 交付物
| 文件 | 说明 |
|------|------|
| `bin/critter` | 游戏主程序（自签 ELF） |
| `share/Critical_Mass/data/*` | 6 个数据子目录（bitmaps/models/sounds/levelpacks/paths/system） |
| `share/Critical_Mass/lg-criti.xm` | 音乐（pkgdata_DATA 自动安装） |

## 注意事项
- SourceForge 官方 /download 直连在 CI/本环境不可靠（HTML 拦截/截断，SHA-256 不符），
  conan get() 会下载到错误内容；conandata.yml 以实测镜像为首选（macports distfiles
  / gentoo lysator 双镜像 2026-09-18 实测 HEAD 200 + Content-Length 5122126 一致，
  官方 /download 兜底）。
- sdl-mixer/1.2.12 未合入 origin/main：若 CI L0i(R36) 按 ohpcd 解析不到该制品，
  属依赖交付缺口（非本库代码问题），需先单独发布 sdl-mixer 或将 sdl-mixer 配方
  并入本 PR。本地 conan cache 已有 sdl-mixer/1.2.12 的 OHOS aarch64 包。
- 上游零测试；版本级验证仅 test_package 的 --version 冒烟（客观限制：游戏需要
  显示/输入设备，无法在非交互沙箱跑真实对局）。
- 沙箱环境限制（不影响 CI）：ohpcd 远端从作者沙箱匿名不可达，CI L0i 探针在 CI
  worker 上执行，本条仅为环境说明。

---

**编译结束**: 2026-09-18（本地 conan create 全流程通过，test_package 1/1）
**最终状态**: built（CI 验证通过并合入后改为 published）
