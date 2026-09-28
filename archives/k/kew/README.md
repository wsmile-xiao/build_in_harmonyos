# Kew

## 简介
Kew 是终端里的音乐播放器（TUI），主体为 C，另有一枚 C++ 的 TagLib 封装；上游构建系统是单个手写 Makefile（无 configure、无 CMake、无 Meson）。依据：`4.2.5/conanfile.py` 的 `description` 与模块 docstring、`4.2.5/notes.md`「货源与哈希」段的实物普查（整棵 tarball：`.c` 55 / `.h` 73 / `.cpp` 2 / `.m` 1）。

## 功能概述
- 播放本地音乐库，封面以字符画呈现（`chafa`）、带频谱（`fftw3f`）与歌词（`src/loader/lyrics.*`）；元数据走 TagLib 并静态吸收进二进制。依据：`commands.json` 的描述、`4.2.5/conanfile.py` 的 `_PKG_MODULES`、`4.2.5/test_package/test_kew.py:166-174`。
- 装机数据树：`bin/kew`、`share/man/man1/kew.1`、`share/kew/themes`、`share/kew/layouts`、`share/locale/{zh_CN,ja}/LC_MESSAGES/kew.mo`、`share/applications/kew.desktop`、`share/icons/hicolor/512x512/apps/kew.png`。依据：`4.2.5/notes.md` 适配点 8、`test_package/test_kew.py:190-205`。
- FAAD2/M4A 是上游可选特性，OHOS 侧以 `USE_FAAD=0` 关闭；MP4/AAC 元数据仍由 TagLib 提供。依据：`4.2.5/conanfile.py` 的 `USE_FAAD=0`、`notes.md` 适配点 7。

## OHOS 适配
- 裸 Makefile 三陷阱（**E392**）与 `make` 统一 `-j1`（**E525**）。`CC`/`CXX` 走 make 命令行；`UNAME_S=Linux` 显式覆盖以保住 PIE/RELRO 加固块。
- `PkgConfigDeps` 只写 `.pc`、不把 generators 目录加进 `PKG_CONFIG_PATH`（**E468**）⇒ 配方在 make 命令里显式导出该变量。
- `PREFIX=<package_folder>` + `USE_FAAD=0`，规避 `/usr/local/lib`、`/opt/homebrew` 硬编码探测（**E524** 前缀注入污染家族）。
- glib 的 gettext 宏落到 `g_libintl_*`，由 `proxy-libintl` 供给（**E142/E508** 家族）；musl loader 本身不导出这些符号。
- 已发布依赖把 `opusfile.h` 装进未导出的 `<pkg>/include/opus` ⇒ 按上游 `.pc` 口径补 `-I`，不动该依赖的配方。
- `STRIP=0`：本机 MAC 拒绝对 strip 后的二进制 `exec`。
- 测试运行环境交接：`env="conanrun"` 给出的 `LD_LIBRARY_PATH` 会抢在 DT_RUNPATH 之前并打断测试解释器自身，故测试脚本先取出再 unset，经 argv 只对被测二进制生效。
- 逐条判决与 RREV 分档见 `4.2.5/notes.md`（本文不重复版本级细节）。

## 能力面与已知边界
- `kew --version` / `kew --help` 在注入 conan run env 后退出码 0，`--help` 输出逐字 `Run man kew for help.`；**不带 run env 的裸跑取不到 DT_NEEDED**，harness 的 L2 smoke 步骤（`ci/conan/build_and_test.sh:1676-1697`）正是裸跑形态，故本地 W3 档 `L2_RESULT=skip: kew version/help failed`（`notes.md` 第 4b 节）。
- 播放主流程结构性不可行：`ls /dev/snd` = Permission denied，`find /system /vendor -name 'libasound*'` 命中 0；miniaudio 的 ALSA 后端运行期靠 `dlopen("libasound.so.2")` ⇒ 链接能过、取不到设备；程序在「Music Library 选择」处打印 `Error reading input.` 后退出。⇒ **不声称能出声**。
- 上游无成体系测试：分母 0、可用 0（`find -iname '*test*'` 的 2 枚命中是文档页，不计入）。

## 依赖关系
- 运行依赖（`requires(..., run=True)`）：`glib`、`chafa`、`fftw3f`、`opus`、`opusfile`、`libvorbis`、`libogg`、`taglib`、`proxy-libintl`、`zlib`。其中 `taglib`、`zlib` 静态吸收，不出现为 DT_NEEDED。
- 构建工具：`pkgconf`（`tool_requires`）。
- 制品里可见 12 枚依赖 soname（来自 8 个包：`glib` 一枚出 4 枚 soname）+ 工具链 `libc++`，即测试里 13 枚前缀的循环断言；另单独断言 musl libc。
- 版本级精确坐标见 `4.2.5/conanfile.py` 与 `4.2.5/manifest.yaml`。

## 功能验证
```bash
kew --version
kew --help
```
需 conan run env（`LD_LIBRARY_PATH`）注入，裸跑取不到 DT_NEEDED。消费者测试为 `4.2.5/test_package/test_kew.py`，36 条断言全绿（装机树、ELF 形态与加固、DT_NEEDED 解析、CLI 自检）。

## 版本
- 4.2.5: built（2026-09-27，B 机本地 `conan create` + W3 绿跑，消费者测试 36/36；未合入前不写 published）。

## 参考资料
- 上游主仓：https://codeberg.org/ravachol/kew（`4.2.5/conanfile.py` 的 `homepage`）
- 取源归档：https://github.com/ravachol/kew/archive/refs/tags/v4.2.5.tar.gz（GitHub 侧为**同名镜像**；tag 归档件哈希经 3 次采样自算一致，见 `4.2.5/notes.md` 第 1 节）
- 许可证：GPL-2.0-or-later（`4.2.5/conanfile.py:101`）
