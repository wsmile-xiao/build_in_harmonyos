# ccaudio 1.2.0 适配笔记

## 编译环境
- **构建系统**: autotools (configure + make)
- **编译日期**: 2026-09-15
- **编译器**: clang（OHOS 工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过——conan create 全绿）
- **补丁数量**: 0（配方内联处理——无独立补丁文件）
- **依赖**: commoncpp2/1.8.1（硬依赖，configure 经 ccgnu2-config 探测）、zlib/1.3.1

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/ccaudio/1.2.0 --build=missing
```

### 1. 源码获取（source()）
```bash
tar -xzf ccaudio-1.2.0.tar.gz --no-same-owner || true
cp -a ccaudio-1.2.0/. . && rm -rf ccaudio-1.2.0
```

### 2. configure 前置处理
- **AutotoolsToolchain(self).generate()（generate() 阶段）**：不生成则
  conanbuild 无 CC/CXX——2006 版 configure 的编译器候选列表不含 clang++，
  报 `C++ compiler cannot create executables`
- **config.sub 补 linux-ohos 模式**（2006 版不识别 ohos 三元组）：
  `linux-gnu*` → `linux-gnu* | linux-ohos*`
- **config.status mktemp 补丁**：`mktemp -d -q "./confstatXXXXXX"` →
  `${TMPDIR}/confstatXXXXXX`（TMPDIR=/data/storage/el2/base/cache）
- **audio.h 宏 fallback**：见"源码修改"节
- **audiofile.cpp 补 include**：见"源码修改"节

### 3. 依赖路径注入（关键）
commoncpp2 的包布局为 `<pkg>/usr/{bin,include,lib}`，且其 ccgnu2-config
脚本内 `prefix="/usr"` 硬编码——`--flags`/`--stdlibs` 输出指向系统目录，
不可用于 conan 包：
```
PATH='<ccxx>/usr/bin:<...>'  # configure 需找到 ccgnu2-config 通过版本检查
CXXFLAGS='-I<ccxx>/usr/include -I<zlib>/usr/include -std=c++98 -fpermissive ...'
LDFLAGS='-L<fixdir> -L<ccxx>/usr/lib -L<zlib>/usr/lib'
./configure --build=aarch64-unknown-linux-ohos --prefix=/usr --disable-shared
```

### 4. libtool .la 修正（generate() 内）
libccext2.la 的 `dependency_libs` 含 `/usr/lib/libccgnu2.la`（构建期绝对
路径）→ libtool 报 `is not a valid libtool archive`。处置：把依赖
`*.la/*.a` 复制到 `<build_folder>/deps-lib`，清空 `dependency_libs`、
`libdir` 指向副本目录，并把该目录放在 LDFLAGS 最前。

### 5. 编译（make -j2）
```bash
make -j2
```

### 6. 上游测试（build() 集成——rule 4/R51 实测回填）
上游测试入口：`src/Makefile.am` 的 `TESTS = wavetest1`（automake check
注册项）+ `noinst_PROGRAMS = wavetest2`（未注册 TESTS 的测试程序）。
两者均为**真实行为测试**：用 AudioFile 写 wav（pcm16Stereo / mulaw）后
按字节逐一比对文件头（43/54 字节）并以退出码判定。

实测结果（build() 内真实执行）：
- `make check` → **wavetest1 通过**（输出 `Test 1 passed.` / `All 1 tests passed`）
- `./wavetest2`（src/ 目录内手动运行）→ **通过**（无 FAIL 输出）

```bash
make check                      # TESTS=wavetest1
cd src && ./wavetest2           # noinst 程序——手动运行
```

### 7. 打包（package()）
```bash
make install DESTDIR=<package_folder>
```
安装布局：`usr/include/cc++2/cc++/audio.h`、`usr/lib/libccaudio1.a`、
`usr/lib/ccaudio1/g.711.so`（MODULES 动态模块）；
cpp_info：includedirs=["usr/include/cc++2"]、libdirs=["usr/lib"]、libs=["ccaudio1"]

## 源码修改（配方内联，不改上游文件本身）
1. **src/audio.h**：头文件保护宏后插
   `#ifndef CCXX_CLASS_EXPORT / #define CCXX_CLASS_EXPORT __EXPORT / #endif`
   （commoncpp2 1.8.1 只提供 __EXPORT；两宏在非 Windows 平台均为
   visibility 属性，静态构建行为一致）
2. **src/audiofile.cpp**：补 `#include <sys/stat.h>/<unistd.h>/<string.h>`
   （musl 不隐式传递，报 incomplete type 'struct stat'）
3. **config/config.sub**：加 `linux-ohos*` 模式
4. **configure/config.status**：mktemp 相对路径 → ${TMPDIR}/

## 验证结果
- **构建**: `ccaudio/1.2.0: Package created`（conan create 全绿）
- **上游测试**: 实测 **2/2 通过**（wavetest1 make check 注册项 +
  wavetest2 noinst 程序——均为真实行为测试，无跳过、无平台受限项）
- **R34 消费者验证**: test_package — 以库使用者身份编译链接并运行
  smoke.cpp（真实调用 AudioFile 公开 API 写 RIFF wav 并读回校验头部），
  输出 `ccaudio AudioFile RIFF round-trip OK`

## 已知限制
- 库以静态方式构建（`--disable-shared`，与 commoncpp2 先例一致）
- 消费者引入头文件需同时提供 commoncpp2 的 include
  （`-I<ccxx>/usr/include`——ost 框架头在 cc++/ 下）
---

**编译结束**: 2026-09-16 00:05
**最终状态**: built
