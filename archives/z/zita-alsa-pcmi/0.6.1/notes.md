# zita-alsa-pcmi 0.6.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，source/Makefile，无 configure 脚本）
- 编译日期: 2026-08-24
- 编译器: /data/service/hnp/bin/clang++（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

纯 Makefile 项目，无 configure。在 `source/` 目录执行：

```bash
make -C source -j1 \
  CXX=<conan profile 的 tools.build:compiler_executables.cpp> \
  CXXFLAGS="-O2 -Wall -fPIC" \
  CPPFLAGS="-D_REENTRANT -D_POSIX_PTHREAD_SEMANTICS -I<alsa-lib>/include" \
  LDFLAGS="-L<alsa-lib>/lib" \
  libzita-alsa-pcmi.so.0.6.1

make -C source install PREFIX=/ LIBDIR=lib DESTDIR=$package_folder
```

install 传参说明：Makefile 用 `$(SUFFIX)`（`uname -m` 推导）拼 `LIBDIR`，传参时固定
`LIBDIR=lib` 避免 aarch64 上产生 `lib64`；`PREFIX=/` + `$(DESTDIR)$(PREFIX)/$(LIBDIR)`
（补丁后）保证安装到 `$DESTDIR/lib` 与 `$DESTDIR/include`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CXXFLAGS += -march=native` | 上游为本地优化编写，交叉/可移植构建不安全 | 补丁移除该行，编译器与优化标志由 Conan profile / 配方控制 |
| 2 | OHOS 无裸 `install` / `ldconfig` 命令 | OpenHarmony PATH 无 coreutils 的 install，ldconfig 不存在 | 补丁引入 `INSTALL ?= /bin/install`（toybox），去掉 `ldconfig` |
| 3 | `make install` 安装到错误路径 | `$(DESTDIR)$(LIBDIR)` 在 `LIBDIR=lib` 时无分隔符拼成 `...plib` | 补丁改为 `$(DESTDIR)$(PREFIX)/$(LIBDIR)`（参照 clthreads） |
| 4 | 缺少 SONAME 符号链接 | 上游只建 `libzita-alsa-pcmi.so` 一个链接，运行时 loader 找不到 `libzita-alsa-pcmi.so.0` | 补丁补全 `.so` → `.so.0` → `.so.0.6.1` 完整链接链（rm -f + ln -s） |
| 5 | init-build 嵌套源码检测误选 `apps/` | tarball 含 `apps/`（示例程序）与 `source/`（库），启发式把 apps 当源码根 | 手动重新解压 tarball，BUILD_SRC_DIR 使用完整结构；配方 source() 用 strip_root 后进 `source/` |
| 6 | refresh-patch --auto 跳过 Makefile | 排除规则把 "Makefile" 当生成文件 | 重建编辑追踪器基线（snapshot→重放修改→track-edit scan），追踪模式精准识别 |

## 源码修改

- `patches/0001-source-Makefile.patch`：移除 -march=native；INSTALL 参数化（默认 /bin/install）；
  去掉 ldconfig；install 目标改用 `$(DESTDIR)$(PREFIX)/$(LIBDIR)`；补全 .so/.so.0/.so.0.6.1 链接链。

## 依赖版本

- alsa-lib/1.2.16（制品仓 ohpcd 已发布，`conan download --only-recipe` 已验证）

## 验证结果

- 编译：libzita-alsa-pcmi.so.0.6.1 生成成功，ELF64/AArch64，SONAME=libzita-alsa-pcmi.so.0
- 上游测试：无（`make check` → "No rule to make target 'check'"），已如实声明
- 消费者测试（staging）：链接 libzita-alsa-pcmi 成功，version API 返回 0.6，
  Alsa_pcmi 构造在无音频硬件设备上优雅降级 STATE_FAIL，运行退出码 0
- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` 本地验证通过

## 注意事项

- 库链接 `-lasound`，运行时需 libasound.so（由 alsa-lib 依赖链提供，conanrun 环境注入）。
- OHOS 无音频硬件时 ALSA 打不开设备属预期，Alsa_pcmi 会返回 STATE_FAIL 而不崩溃。
- conandata.yml sources.url 已从本地缓存 file:// 路径改为官方源
  https://kokkinizita.linuxaudio.org/linuxaudio/downloads/zita-alsa-pcmi-0.6.1.tar.bz2
  （R39：官方源，sha256 不变，HTTP 200 实测可达；file:// 为本机专用，CI 无法复现）。
  2026-08-25 复验 conan-verify G0-G4 全 PASS，test_package "zita-alsa-pcmi 0.6 OK (state=1)"。
---

**编译结束**: 2026-08-25 12:38
**最终状态**: built
