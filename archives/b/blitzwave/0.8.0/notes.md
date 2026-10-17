# blitzwave 0.8.0 适配笔记

## 编译环境
- 构建系统: autotools（上游仅带 configure.ac + autogen.sh，无生成 configure/Makefile.in）
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，OHOS SDK sysroot aarch64-linux-ohos）
- 状态: built
- 任务环境: 鸿蒙设备单端；worktree `wt-blitzwave-0.8.0`，分支 `feat/blitzwave-0.8.0`

## 上游信息
- 源: https://github.com/oschulz/blitzwave/archive/refs/tags/v0.8.0.tar.gz
- SHA-256: `edb0b708a0587e77b8e0aa3387b44f4e838855c17e896a8277bb80fbe79b9a63`（下载实测，与 homebrew 配方一致；macports 同 tag 打包形态不同 sha256=daacce4f...，不可混用）
- 上游 master 比 v0.8.0 tag 多 2 个提交（"Improved build system" 等，引入 m4/cxx-project-*.m4），本适配严格基于 tag v0.8.0 tarball
- 上游 issue #2（Doesn't build with newer automake）即本包 AM_PROG_AR 补丁对应问题；homebrew/macports 均打同款补丁

## 编译步骤

原生探索（$HOME/tmp/task-blitzwave-0.8.0/explore/，-j1）：

```bash
# 1. 打 AM_PROG_AR 补丁（configure.ac，AC_PROG_CXX 前插一行）
# 2. autoreconf --install --force        # 生成 configure/Makefile.in/config.h.in 等
# 3. 移除生成 configure 中的 umask 077（E114）
# 4. CC=clang CXX=clang++ CXXFLAGS="-I<blitz>/include" LDFLAGS="-L<blitz>/lib" \
#    ./configure --prefix=... --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
# 5. make -j1 && make install
```

Conan 路径（同 SHA 验证）：`conan create` 内 conanfile.build() 复刻以上步骤；automake/1.18 + libtool/2.5.4 走 tool_requires；blitz/1.0.2 为 requires。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 硬失败（automake -Werror 把 "AM_PROG_AR required" 升级为错误；homebrew 上游 issue #2 同因） | automake >= 1.12 + `AM_INIT_AUTOMAKE([-Wall -Werror])` | patch 0001 在 configure.ac 的 AC_PROG_CXX 前插入 `AM_PROG_AR`（macports 位置；homebrew 放 LT_INIT 后会出 "LT_INIT was called before AM_PROG_AR" 告警） |
| 2 | configure 首跑即 `cannot guess build type`（uname -s = HarmonyOS，uname -r = HongMeng Kernel 1.12.0） | config.guess 2025-07-10 无 HarmonyOS 识别 | 显式 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`（automake 1.18 config.sub 实测接受；与 boolstuff/clarisworks 先例一致） |
| 3 | config.status: `can't create ./confXXXX/subs1.awk: Permission denied`（E114） | autoconf AS_TMPDIR 的 `umask 077` + HMDFS setgid：0700 临时目录落盘为 drwx--S--- 不可写 | build() 在 autoreconf 后对生成的 configure 做文本替换去掉 `umask 077`（clarisworks 同款 `_drop_umask_077`） |
| 4 | `checking for main in -lblitz... no` 风险 | conan blitz 包只带 libblitz.a，无 blitz.pc/blitz-config；configure 的 pkg-config/blitz-config 探测全落空 | configure 走 `AC_CHECK_LIB(blitz, main)` 兜底；-I/-L 由 AutotoolsToolchain `extra_cxxflags`/`extra_ldflags` 注入（AutotoolsToolchain 不自动聚合依赖 cpp_info） |
| 5 | profile buildenv `CONFIG_SHELL=/data/service/hnp/bin/bash` | bash 下老 ltmain 生成的 libtool 会丢引号转义（boolstuff E551 先例） | configure 用命令行前缀赋值 `CONFIG_SHELL=/bin/sh` 调用 |
| 6 | 并行 make 触发 HMDFS jobserver fifo EPERM（E074） | HMDFS 不支持 jobserver fifo | `make -j1` |

## 源码修改

- `patches/0001-configure-ac-add-AM_PROG_AR.patch`：configure.ac 插入一行 `AM_PROG_AR`（patch_ng strip=1 本地库调用验证通过）。
- 无其他源码修改；未改上游测试。

## 时间戳说明

补丁只触及 configure.ac 且在 `autoreconf --install --force` 之前应用：autoreconf 随后重建 aclocal.m4/configure/config.h.in/Makefile.in（mtime 均新于 configure.ac），configure 又生成 Makefile/config.h——maintainer 规则不会触发，无需 boolstuff 式全链 pin 时间戳。原生与 conan 两轮构建均未见任何规则重生成。

## 依赖版本

- blitz/1.0.2（ohpcd，OHOS binary，静态库形态 libblitz.a；W0 用 `conan install --build=never` 实证）
- automake/1.18、libtool/2.5.4（tool_requires，OHOS build profile binary 实证可装）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libcxx=libc++, cppstd=17）

## 上游 C++ 标准核对

上游代码（2003-2008）无 C++17 移除特性（无动态异常规范/auto_ptr/random_shuffle/register）；clang 15 默认 gnu++17 下原生编译零告警通过。与 profile cppstd=17 无冲突，无需标准改写。

## 验证结果

### 上游测试（无测试框架；三个 noinst 自测程序，单位=程序，TOTAL=3）

上游 0.8.0 的 src/Makefile.am 只声明 `noinst_PROGRAMS`（无 TESTS/check_PROGRAMS，`make check` 为空跑），测试随 `make all` 构建，逐个手工执行：

| 程序 | 判定 | 结果 |
|------|------|------|
| Wavelet-test | 退出码 0 + 打印 CDF(1,1)/CDF(2,2) 提升格式 + 2 assert | PASS（assert 全过） |
| WaveletDecomp-test | 退出码 0 + MaxDiff(must be <<1)=0/0 + 量化 MaxDiff=4、StdErr=0.012 + 深度 (9,9,0)/(-9,-9,0) 互逆 + 无 Exception 输出 | PASS |
| arrayTools-test | 退出码 0 + 切片/重索引/滤波/fill 输出正常 + 无 Exception 输出 | PASS |

TOTAL=3 PASS=3 FAIL=0 SKIP=0 NOT_RUN=0

假绿防御：WaveletDecomp-test/arrayTools-test 的主体在 try/catch 内且无 assert，异常被吞后仍退出 0——采信以实质输出核对为准（两轮均逐项核对）。arrayTools-test 的输入 intdata.txt 上游 tarball 与 git 仓库均缺失，由 conanfile build() 生成 256 点确定性整数信号（(i*37)%256）作为补充 fixture；WaveletDecomp-test 的 testimage.pnm 为 tarball 自带，经 argv[1] 传入。

### 消费者验证（test_package + 原生）

- test_package 消费者：链接 `blitzwave::blitzwave + blitz::blitz`，1-D CDF(2,2) 完美重构 maxdiff=4.441e-16 < 1e-10；2-D 选维分解+分离系数往返 maxdiff=1.137e-13 < 1e-8；描述符恒等式（WL_HAAR==WL_CDF_1_1 等）通过；输出 PASS（数值与 reports/conan-create.log 采信轮一致）。
- 原生共享库验证：dlopen libblitzwave.so.0 成功；readelf: NEEDED = libc++_shared.so/libc.so，SONAME = libblitzwave.so.0；hnp clang 产物自带 .codesign 节（禁止重签）。

## 交付物

| 文件 | 说明 |
|------|------|
| include/blitzwave/{Wavelet.h,WaveletDecomp.h,arrayTools.h} | pkginclude_HEADERS（include/blitzwave/） |
| lib/libblitzwave.a | 静态库（shared=False 变体；shared 变体同带静态库以满足上游测试 -static 链接） |
| lib/libblitzwave.so.0.0.0（+符号链接） | 共享库（shared=True 变体） |
| bin/blitzwave-config | 上游库配置脚本（--version/--cflags/--libs 实测可用） |

不打包：lib/*.la（libtool 残留）、lib/pkgconfig/blitzwave.pc（固化缓存期 prefix 且无条件列 -lblitz，对 conan 消费者有误导，消费者经 CMakeDeps 获得正确传递依赖）、share/doc（精简）。

## 注意事项

- shared=True 变体保留静态库：上游测试程序 `_LDFLAGS = -static` 需要 .a，禁用 static 会直接破坏测试构建。
- conandata.yml 无 sources 之外的裸 URL；patches 为 Conan 官方版本字典形态。
- 上游 master 的 "Improved build system" 提交重构了 configure.ac 并加 m4 宏，但未发布；本适配不引入未发布改动。
