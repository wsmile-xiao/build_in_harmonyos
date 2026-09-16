# sdl-image 1.2.12 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-13
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码：`https://www.libsdl.org/projects/SDL_image/release/SDL_image-1.2.12.tar.gz`
   （sha256 `0b90722984561004de84847744d566809dbb9daf732a9e503b91a1b5a84e5699`）。
2. 依赖注入（`generate()`）：只注入 `SDL_CFLAGS`/`SDL_LIBS`（由 `sdl12-compat` 的
   `cpp_info.cflags`/`cpp_info.libs` 拼出），不设置 `SDL_CONFIG`——`pkg-config sdl` 在本环境
   不存在，而依赖包自带的 `sdl-config` 输出的是构建期路径，故绕开两者直接给编译/链接标志。
3. 配置：显式双三元组 `--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
   （见「遇到的问题」#2），`--disable-*-shared` 让四个编解码器成为链接期依赖。
4. 编译安装：`make -j1` → `make install`（autotools 布局，产物由 Conan 打包）。
5. 验证：`conan create ... -pr:h=ci/conan/profiles/ohos-aarch64`，随后 `test_package`
   运行消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Invalid configuration 'aarch64-unknown-none'` | 上游 2012 版 `config.sub` 早于 aarch64/OHOS，不认识新 CPU/OS 段 | `patches/0001-config.sub.patch` 补 `aarch64` CPU 段、`-linux-ohos` OS 段，并在末尾 `-linux*)` 归一化分支前追加 `-linux-ohos)` 守卫（详见下方"config.sub 归一化实测"） |
| 2 | `config.status: ./confXXXXXX/out: Permission denied`，Makefile 未生成 | `config.guess` 把构建机识别为 HarmonyOS，configure 以为在本地编译，于是 conftest 走 `config.status`，其用 `mktemp -d`（0700）建临时目录，而本平台 HMDFS 挂载下 0700 目录不可写 | 不改 `config.guess`，改为显式传 `--build`/`--host` 双三元组，强制 autoconf 交叉模式，绕开 conftest 运行检查（仓库既有先例：aalib 1.4p5） |
| 3 | configure 探测不到 SDL 1.2 | `pkg-config sdl` 不存在；依赖自带 `sdl-config` 输出构建期路径 | 由配方直接注入 `SDL_CFLAGS`/`SDL_LIBS`/`SDL_CONFIG` |
| 4 | 消费者编译报 `'SDL.h' file not found` | 已发布的 `sdl12-compat/1.2.68` 头文件位于包内 `include/SDL/`，但其 `cpp_info.includedirs` 为空，CMakeDeps 无 include 目录可导出 | 在 `test_package/generate()` 中用 `self.dependencies["sdl12-compat"].package_folder` 计算 `SDL1_INCLUDE_DIRS` 传给 CMake；不在被测包内越界声明依赖的 cpp_info（依赖元数据修正应单独提 PR） |

## 源码修改

- `patches/0001-config.sub.patch`（4 处 hunk）：为 `config.sub` 增加 `aarch64` CPU 段、
  `-linux-ohos` OS 段（maybe_os 列表与 OS 合法列表各一处），并在末尾 `-linux*)` 归一化分支之前
  插入 `-linux-ohos)` 守卫分支，使 `--host=aarch64-linux-ohos` 归一化为 `aarch64-unknown-linux-ohos`。
  仅改 `config.sub`，`config.guess` 保持原始以最小化补丁；补丁不含任何平台宏（纯可移植性修复）。
- `patches/0002-configure.patch`（1 处 hunk，2 行）：把 `configure` 里的 `umask 077` 全部改为
  `umask 022`。configure 会把这段文本原样写进它生成的 `config.status`，而 `config.status` 用
  `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；HMDFS 下 0700 目录归 uid 20001006 且对
  构建进程不可写（`chmod` 不生效），表现为 configure 打印成功但 Makefile 从未生成
  （`./confW5skaH/subs-1.sed: Permission denied`）。属平台通用坑（知识条目 E011），
  纯可移植性修复，不含平台宏。
- 其余源码未改动。

## config.sub 归一化实测

末尾 `case $os in` 中 `-linux*)` 分支会执行 `sed -e 's|linux|linux-gnu|'`。补丁为该分支加了
`-linux-ohos)` 守卫（仓库先例：`at/3.2.5`、`acpitool/0.5.1` 的 `0002-config.sub.patch`）。

对照实验（同一份补丁，仅移除 OS 合法列表里的 `-linux-ohos*` 条目）：

| 场景 | `config.sub` 输出 |
|------|------------------|
| 完整补丁（含白名单条目） | `aarch64-unknown-linux-ohos` |
| 仅移除白名单条目 | `aarch64-unknown-linux-gnu-ohos` (退化) |
| 完整补丁 + 守卫分支 | `aarch64-unknown-linux-ohos` |

结论与实测证据：

- OS 合法列表条目（第三个 hunk）本身即可阻止 `-linux*)` 改写：`case` 首个匹配生效，
  该条目位于 `-linux*)` 之前，命中后不再落到改写分支（这正是 flactag 类"必须删分支"差异所在）。
- 实际构建产物 `config.status` 记录 `host_alias='aarch64-unknown-linux-ohos'`、`host_os='linux-ohos'`，
  归一化结果与补丁声明契约一致，无 `linux-gnu-ohos` 残留。
- 守卫分支是白名单之外的**显式**保险：即便后续白名单被改动，`-linux-ohos` 也不会被
  `sed 's|linux|linux-gnu|'` 改写。两者叠加，语义与仓库既有先例写法一致。

## config.status 临时目录（umask）修复

现象：configure 正常打印 `checking ... yes` 并以 `configure: creating ./config.status` 收尾，但紧接着
`./config.status: line 668: ./confW5skaH/subs-1.sed: Permission denied` 与
`sed: Makefile: No such file or directory`，最终 `make: *** No targets specified and no makefile found`。

根因：autoconf 生成的 `config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录。
本平台（HMDFS）新建对象 owner 固定映射为 uid 20001006:file_manager，0700 目录对构建进程不可写，
且 `chmod` 不生效。属平台通用坑（非本包特例），知识条目 E011 的规范解法即
`sed -i 's/umask 077/umask 022/g' configure`——configure 会把该文本原样写进它生成的 config.status，
一处源码补丁同时修掉 configure 期与 config.status 期。

实测对照（同一目录，仅 umask 不同）：

| 建目录方式 | 目录模式 | 目录内可写 |
|-----------|---------|-----------|
| `umask 077 && mkdir d` | `drwx--S---` | ❌ |
| `umask 077 && mktemp -d dXXXXXX` | `drwx--S---` | ❌（本次失败现场） |
| `umask 022 && mktemp -d dXXXXXX` | `drwxr-s--x` | ✅ |
| `umask 022 && mkdir d` | `drwxr-s--x` | ✅ |

下发方式：`patches/0002-configure.patch`（源码补丁，非环境 hack），本地 W3 与 CI 同源生效。

## 依赖版本

- sdl12-compat/1.2.68（SDL 1.2 API 提供者）
- libpng/1.6.58（zlib/1.3.1.1）
- libjpeg-turbo/3.2.0
- libtiff/4.7.2
- libwebp/1.6.0

## 验证结果

```bash
$ conan create archives/s/sdl-image/1.2.12 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --build="sdl-image/*"
# configure: SDL yes / jpeglib yes / png yes / tiffio yes / webp yes
# test_package: 常规消费者测试 8/8 + HarmonyOS 专项消费者测试 5/5 通过
# IMG_Init() == 0x0f，PNG(libpng) 与 BMP(内置) 解码 3x2
# conan create 成功，状态 published
```

- 上游无测试套件（`noinst_PROGRAMS = showimage`，`TESTS` 为空）；未修改 CI 白名单文件，版本级 `test_package/MANIFEST.yml` 记录上游测试为 0，并由两个消费者测试场景承担验证：常规 API 消费者测试 8 项断言 + HarmonyOS 专项消费者测试 5 项断言。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libSDL_image.a` | 静态库 | 库类默认静态，避免与系统同名库冲突 |
| `include/SDL/SDL_image.h` | 头文件 | 供消费者使用 |

## 注意事项

- 上游 1.2.12 是 SDL 1.2 分支的最终版本；SDL 2/3 对应 `SDL2_image`/`SDL3_image`。
- 本包**未声明**依赖 `sdl12-compat` 的 include 目录缺口修复，消费者如遇 `SDL.h` 缺失，
  需自行从 `dependencies["sdl12-compat"].package_folder` 定位（详见知识草稿
  `knowledge/drafts/sdl-image-1.2.12-autotools-cross-ohos.kv`）。
- `test_package` 内对该依赖头文件路径的兜底是为了让消费者测试可编译，属测试侧适配，
  不代表被测包导出了别人的头文件路径。
---

**编译结束**: 2026-09-13 16:48
**最终状态**: published
