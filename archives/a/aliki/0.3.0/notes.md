# aliki 0.3.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，source/Makefile，无 configure 脚本）
- 编译日期: 2026-08-31
- 编译器: /data/service/hnp/bin/clang++（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

纯 Makefile 项目，无 configure。在 `source/` 目录执行：

```bash
make -C source -j1 \
  CXX=<conan profile 的 tools.build:compiler_executables.cpp> \
  PCONFCFL="-I. -I<clxclient>/include -I<clthreads>/include -I<libsndfile>/include \
            -I<fftw3f>/include -I<libxft>/include -I<libx11>/include -I<xorgproto>/include \
            -I<zita-alsa-pcmi>/include -I<jack>/include -I<alsa-lib>/include" \
  LDFLAGS="-L<每个依赖>/lib ..." \
  all

make -C source install PREFIX=/ LIBDIR=lib DESTDIR=$package_folder
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CXXFLAGS += -march=native` | 上游为本地优化编写 | 补丁移除该行，编译器与优化标志由 Conan profile / 配方控制 |
| 2 | `aliki` 目标硬编码 `-I/usr/include/freetype2` 与 `-L/usr/X11R6/lib...` | 桌面路径在 OHOS 不存在 | 补丁移除，头/库路径由配方按依赖包注入 |
| 3 | 链接用硬编码 `g++` | CI 无 g++（R33） | 补丁改用 `$(CXX)`，配方从 conf 取 clang++ |
| 4 | OHOS 无裸 `install` 命令 | OpenHarmony PATH 无 coreutils 的 install | 补丁引入 `INSTALL ?= /bin/install`（toybox） |
| 5 | 命令行覆盖 CPPFLAGS 会丢 `-DVERSION` | make 命令行变量优先级最高 | 补丁新增 `$(PCONFCFL)` 槽位（追加进 CPPFLAGS），配方经它注入 include 路径 |

## 依赖版本

- clxclient/3.9.2（本任务先适配发布，见 archives/c/clxclient）
- clthreads/2.4.0、libsndfile/1.2.2、fftw3f/3.3.9、libxft/2.3.8、libx11/1.8.13、
  xorgproto/2025.1、zita-alsa-pcmi/0.6.1、jack/1.9.22、alsa-lib/1.2.16
  （制品仓 ohpcd 均已发布，`conan download --only-recipe` 已验证）

## 验证结果

- 编译：`aliki` 与 `aliki-rt` 两个 ELF64/AArch64 可执行文件生成成功
- 上游测试：无（`make -C source check` → "No rule to make target 'check'"），已如实声明
- 消费者测试（test_package）：staging 完整运行时闭包并 ELF 签名；
  `aliki -h` 输出版本横幅 "Aliki-0.3.0"（上游 help() 退出 1，横幅即断言）；
  `aliki-rt` 无参退出 1（缺共享内存参数，非 127 loader 错误）
- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` 本地验证通过

## 注意事项

- aliki 是 X11 GUI 应用，需显示服务器；aliki-rt 需音频硬件与共享内存。OHOS/CI 无
  这些设施，运行时测试以「加载完整闭包并到达正常提前退出路径」为通过标准。
- commands.json 声明两个命令行工具（aliki / aliki-rt），R38 合规。
- conandata.yml sources.url 为官方源
  https://kokkinizita.linuxaudio.org/linuxaudio/downloads/aliki-0.3.0.tar.bz2
  （R39：官方源，sha256 与本地实测一致，HTTP 200 可达）。

---

**编译结束**: 2026-08-31
**最终状态**: built
