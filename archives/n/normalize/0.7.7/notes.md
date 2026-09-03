# normalize 0.7.7 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，2005 版 autotools）
- 编译日期: 2026-09-03
- 平台: HarmonyOS PC / OHOS aarch64（HongMeng Kernel 1.12.0，uname -s = HarmonyOS）
- 编译器: clang 15（-fPIC -O2）
- 状态: published

## 编译步骤

1. 下载权威镜像源码（Debian pool orig tarball，上游 SourceForge downloads 不可达）：
   `https://deb.debian.org/debian/pool/main/n/normalize-audio/normalize-audio_0.7.7.orig.tar.gz`
   sha256=6055a2abccc64296e1c38f9652f2056d3a3c096538e164b8b9526e10b486b3d8
2. 修改源码（两处，见补丁）：
   - `config/config.guess`：增加 aarch64:HarmonyOS / aarch64:Linux 识别，输出 aarch64-unknown-linux-gnu；
   - `configure`：config.status 临时目录 `umask 077` → `umask 000`。
3. 依赖 audiofile/0.3.6（制品仓已发布）：`conan install` 到本地，生成 `audiofile-config` shim
   加入 PATH 供 AM_PATH_AUDIOFILE 宏使用。
4. 手动验证命令（native）：
   ```bash
   export PATH=<afbin>:$PATH
   LIBS="-lc++" ./configure --prefix=$DEFAULT_PREFIX
   make -j2
   make install DESTDIR=$TEST_PREFIX
   make check   # 3/3 passed（test8bit/test16bit/test24bit），test-tools SKIP
   ./src/normalize --version
   ```
   配置结果确认：USE_AUDIOFILE=1、非 WORDS_BIGENDIAN（小端实测）、SIZEOF_LONG=8（LP64 实测）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `/bin/bash: inaccessible` | 本机无 /bin/bash | 不设 CONFIG_SHELL=/bin/bash，用 configure 自带的 #!/bin/sh 直接执行 |
| 2 | config.guess 无法识别平台 | uname -s=HarmonyOS，2005 版 config.guess 无 aarch64/HarmonyOS 分支 | 补丁增加 `aarch64:HarmonyOS:*:*` 与 `aarch64:Linux:*:*` → 输出 aarch64-unknown-linux-gnu（同 audiofile 0001 方案） |
| 3 | config.status: `can't create ./confstatXXXXXX/out: Permission denied` | config.status 用 `umask 077 && mktemp -d` 建临时目录，HMDFS 上该目录属主不同、构建用户不可写（同 audiofile 0002 场景） | 补丁 `umask 077`→`umask 000` |
| 4 | 链接失败：`undefined symbol: operator new/delete, std::string...`（来自 libaudiofile.a） | audiofile 静态库由 C/C++ 混编对象组成，normalize 用 C 链接驱动，未带 libc++ | configure 时 `LIBS="-lc++"`（放在 LIBS 而非 LDFLAGS——LDFLAGS 出现在归档之前无法解析静态库符号） |
| 5 | conan 依赖包未提供 `audiofile-config` 脚本 | AM_PATH_AUDIOFILE 宏（老式）只认 audiofile-config --cflags/--libs/--version | 配方 generate() 生成私有 shim 指向 audiofile 包目录，注入 PATH + AUDIOFILE_CONFIG |

## 源码修改（补丁）

- `patches/0001-config-config.guess.patch`：config.guess 增加 HarmonyOS/aarch64 平台识别（portability）
- `patches/0002-configure.patch`：config.status 临时目录 umask 077→000（portability，HMDFS）

无 `#ifdef __OHOS__` 平台宏（R8）。

## 依赖版本

- audiofile/0.3.6（revision ee9e93a26e8275e446596583ee294923，制品仓已发布）

## 验证结果

```bash
$ make check
PASS: test8bit.sh
PASS: test16bit.sh
PASS: test24bit.sh
SKIP: test-tools   # 需要外部转换工具（madplay/lame/flac/oggenc），未打包故跳过
All 3 tests passed

$ ./src/normalize --version
normalize 0.7.7  ... compiled with the following libraries: audiofile
```

产物：`bin/normalize`（arm64 ELF，动态解释器 /lib/ld-musl-aarch64.so.1）、`bin/normalize-mp3`（脚本）、man 手册。
conan-verify 8 道门禁与 W3 conan create 均通过（详见 reports/）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application，requires audiofile/0.3.6，generate() 生成 audiofile-config shim，make check 集成） |
| conandata.yml | 源码 URL + sha256 + 补丁声明 |
| test_package/ | 消费者功能测试（实质运行 normalize 二进制） |
| patches/0001-*.patch, 0002-*.patch | 平台适配补丁 |
| ../commands.json | 命令行工具声明（R38，type=tool） |

## 注意事项

- 本包不打包 libmad / xmms 插件（可选依赖，未在制品仓）。
- ELF 未在配方内做 .codesign 签名：本机为开发者模式可直跑；发布流水线 sign.sh 负责签名。
- normalize-mp3/normalize-ogg 是辅助脚本，需要外部转换工具时才可用（与上游一致）。
---

**编译结束**: 2026-09-03 16:39
**最终状态**: built
