# aeolus 0.10.4 适配笔记

## 编译环境
- 构建系统: makefile（无 configure 脚本，纯 Makefile；源码位于 tarball 的 `source/` 子目录）
- 编译日期: 2026-08-25
- 编译器: clang/clang++（`/data/service/hnp/bin/`，OHOS SDK 26.0.0.18 llvm 15，来自 conan profile `tools.build:compiler_executables`）
- 目标平台: HarmonyOS PC aarch64（os=OHOS, arch=armv8）
- 状态: built

## 编译步骤

```bash
source .build-context-aeolus-0.10.4
# 1) 探明 tarball 结构：aeolus-0.10.4/source/Makefile（根目录还有 README/INSTALL/COPYING/AUTHORS）
#    conan `get(strip_root=True)` 提取后 Makefile 位于 <sf>/source/Makefile，补丁路径对应 a/source/Makefile
# 2) 用编辑追踪器建立基线（snapshot→重放原文件→track-edit scan），refresh-patch --auto 生成补丁
# 3) 探索性编译（等价于 conan build() 内的命令，flags 走环境变量使 Makefile `+=` 生效）：
#    CPPFLAGS="-DCLTHREADS_NO_PTHREAD_CANCEL -I<zita>/include -I<clthreads>/include ..." \
#    LDFLAGS="-L<zita>/lib -L<clthreads>/lib -L<jack>/lib -L<alsa>/lib -L<readline>/lib -L<ncurses>/lib" \
#    make -C source -j1 CXX=/data/service/hnp/bin/clang++ LIBDIR=lib aeolus aeolus_txt.so
# 4) make install PREFIX=/ BINDIR=bin LIBDIR=lib DESTDIR=$TEST_PREFIX
#    （lib 固定覆盖 Makefile 里 $(PREFIX)/lib$(SUFFIX) 的 SUFFIX 拼接）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CXXFLAGS += -march=native` | 上游面向本机编译，交叉/容器环境不可移植 | portability 补丁移除（refresh-patch --auto 生成），编译器由 profile 提供（R33） |
| 2 | `aeolus_x11.so` 无法构建 | 依赖 X11/Xft/clxclient，制品仓与 OHOS SDK 均无头文件/库 | 平台限制：只构建 `aeolus` 主程序 + `aeolus_txt.so`，install 目标剔除 x11；见 R40 评估 |
| 3 | 直接 `make ... CPPFLAGS=...` 编译时 VERSION/LIBDIR 未定义 | make 命令行变量覆盖 Makefile 的 `CPPFLAGS += -DVERSION... -DLIBDIR...`（`+=` 追加丢失） | flags 通过环境变量传入而非 make 命令行变量 |
| 4 | `aeolus_txt.so` 链接报 undefined: tputs/tgetent/PC/BC/UP | readline 配方为静态库，termcap 符号需 ncurses | Makefile `aeolus_txt.so` 的 LDLIBS 补 `-lncursesw`，配方显式 requires ncurses/6.6 |
| 5 | `make install` 产物变成 `...4bin/...4lib`（缺斜杠） | 原 install 目标 `$(DESTDIR)$(BINDIR)` 无分隔斜杠 | 补丁改为 `$(DESTDIR)/$(BINDIR)` |
| 6 | 缺 `install`/`ldconfig` | OHOS 无裸 install（toybox 为 /bin/install），无 ldconfig | 补丁 `INSTALL ?= /bin/install`，去掉 `ldconfig $(PREFIX)/$(LIBDIR)` |
| 7 | clthreads.h 内 `pthread_cancel` 未声明 | OHOS 无 pthread_cancel | CPPFLAGS 加 `-DCLTHREADS_NO_PTHREAD_CANCEL`（与 clthreads/2.4.0 配方同法） |

## 源码修改

- `patches/0001-source-Makefile.patch`（portability，由 `refresh-patch --auto` 生成）：
  - 删除 `CXXFLAGS += -march=native`
  - `INSTALL ?= /bin/install` 参数化；install 目标去掉 `ldconfig`，改用 `$(DESTDIR)/$(BINDIR|LIBDIR)`
  - install 只构建/安装 `aeolus` + `aeolus_txt.so`（剔除 `aeolus_x11.so`）
  - `aeolus_txt.so` LDLIBS 追加 `-lncursesw`

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zita-alsa-pcmi | 0.6.1 | ALSA PCM 封装（-lzita-alsa-pcmi） |
| clthreads | 2.4.0 | 线程/IPC（-lclthreads，-DCLTHREADS_NO_PTHREAD_CANCEL） |
| jack | 1.9.22 | JACK 音频（-ljack） |
| alsa-lib | 1.2.16 | ALSA 音频（-lasound） |
| readline | 8.3 | 文字界面行编辑（静态库） |
| ncurses | 6.6 | readline 的 termcap 符号（-lncursesw） |

## 验证结果

```bash
# make check：上游无此目标（已确认）
$ make check
make: *** No rule to make target 'check'.  Stop.
# 因此 MANIFEST.yml 声明 upstream_test_in_build=false，验证由 test_package/ 承担。

# 探索性验证（本地）
$ LD_LIBRARY_PATH=... ./aeolus -h   # 打印 "Aeolus 0.10.4" 帮助（上游 help() 退出码为 1，断言以横幅文本为准）
$ dlopen(aeolus_txt.so) + dlsym("create_iface") → 成功

# test_package（conan create 自动运行）：
#   1) 运行 package bin/aeolus -h（grep 断言输出含 "Aeolus 0.10.4"，不校验退出码）
#   2) dlopen package lib/aeolus_txt.so，解析 create_iface
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/aeolus | 主程序（JACK/ALSA 管风琴合成器） |
| lib/aeolus_txt.so | 文字模式界面插件 |

## R40 深度适配评估（aeolus_x11.so）

- **平台限制证据**：
  1. 制品仓无 X11 相关包：`conan download xft -r=ohpcd --only-recipe` / `conan download libxft -r=ohpcd` → `0 recipes`（查无配方）
  2. 本机与 OHOS SDK 均无 X11/Xft 头文件：`find /data/service/hnp /storage/Users/currentUser/usr/local -name "X11" -o -name "Xft"` 无结果
  3. aeolus_x11.so 依赖链：`-lclthreads -lclxclient -lXft -lX11` + freetype2，clxclient 亦无配方
- **结论**：x11 GUI 依赖 X11 窗口系统，OpenHarmony 无此环境；核心合成器功能（JACK/ALSA 音频 + aeolus_txt.so 文字界面）不受影响，aeolus_x11.so 属平台限制跳过，非适配失败。

## 注意事项

- Makefile 无 configure，`.build-context` 中 `BUILD_SYSTEM=autotools` 与实际（makefile）不一致，配方以 conanfile.py/MANIFEST 为准。
- 运行 aeolus 时 LIBDIR 编译为 "lib"（相对），插件默认按相对路径查找；test_package 直接用 package 内绝对路径 dlopen 验证。
---

**编译结束**: 2026-08-25 11:42
**最终状态**: built
