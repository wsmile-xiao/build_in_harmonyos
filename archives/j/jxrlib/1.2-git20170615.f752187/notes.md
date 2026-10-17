# jxrlib 1.2-git20170615.f752187 适配笔记

## 源码定性

- 上游：https://github.com/4creators/jxrlib （JPEG XR DevPK 参考实现的
  官方 GitHub 仓库，维护者 Jacek Blaszczynski）。本适配固定快照
  `f7521879862b9085318e814c6157490dd9dbbdb4`（2017-06-15 "Create
  README.md"，上游最后一次提交；tarball sha256
  `8ab20a21f6c3f8cfdedd2511b03a2009e52cce7fa6550202c355063d0d83213e`，
  本机 codeload 与 github.com archive 两个 URL 下载逐字节一致）。
  该快照即 Debian `jxrlib 1.2~git20170615.f752187` 的上游来源；版本号
  按赛事命名规范写作 `1.2-git20170615.f752187`。
- 上游 2017-06-15 后停更，快照即最终状态。
- License: BSD-2-Clause（归档内 LICENSE；Makefile 头注释同）。
- 无运行时依赖：纯 C，仅链接系统数学库 `-lm`；W0 确认依赖集为空。

## 构建系统与适配步骤

1. **裸 Makefile**（无 configure/CMake；`make` 目标只有
   all/clean/install）。补丁 `patches/0001-ohos-portability-and-version.patch`：
   - **工具链接线（R33）**：`CC=cc` → `CC ?= cc`，新增 `AR ?= ar`、
     `RANLIB ?= ranlib`；CFLAGS 尾部追加 `$(EXTRA_CFLAGS)`；两条
     `-shared` 链接规则与两条工具链接规则追加 `$(EXTRA_LDFLAGS)`；
     `ar rvu`/`ranlib` 改用 `$(AR)`/`$(RANLIB)`。配方 build() 经
     `env="conanbuild"` 传入 `EXTRA_CFLAGS="$CFLAGS $CPPFLAGS"`、
     `EXTRA_LDFLAGS="$LDFLAGS"`。上游 CFLAGS 自带的
     `-I. -Icommon/include -Iimage/sys -D__ANSI__
     -DDISABLE_PERF_MEASUREMENT` 原样保留（R1 参数最少化）。
   - **新工具链隐式声明修复**：`image/decode/segdec.c` 使用
     `strcodec.c` 中定义（但无任何头文件声明）的 `_byteswap_ulong`；
     现代 clang（含 OHOS clang 15）对隐式声明直接报错。在 segdec.c
     顶部加 `extern U32 _byteswap_ulong(U32 bits);`。BIG__ENDIAN
     平台该 extern 不参与链接，安全。
   - **缺失包含**：`jxrgluelib/JXRGlueJxr.c` 用 `wcslen` 却未包含
     `<wchar.h>`（补 `<wchar.h>` 与 `<stdlib.h>`）。
   - **headless 版本探针**：`JxrDecApp`/`JxrEncApp` main 参数解析前
     加 `--version`（打印 `jxrlib 1.2-git20170615.f752187` 退出 0，
     darkhttpd/divxcomp 先例），供 L2 冒烟。
   - 补丁不携带任何平台宏（R8/PF5 口径），全部为可移植性修改。
2. **package()**：按上游 `make install` 树安装头文件
   （`include/libjxr/{common,image,image/x86,glue,test}`，与
   `libjxr.pc.in` 的 Cflags 一致）；库与工具装 lib/、bin/；LICENSE 进
   licenses/。未调用上游 install 目标（默认 `DIR_INSTALL` 指向绝对路径
   且 pc 文件用 python 生成，与本包无关；Conan 消费走 cpp_info）。
3. **package_info()**：5 个 includedirs + `libs=["jxrglue","jpegxr"]`
   （静态链接顺序：glue 依赖 codec）+ `system_libs=["m"]` +
   `defines=["__ANSI__","DISABLE_PERF_MEASUREMENT"]`（结构体 ABI 锁定，
   与 pc 文件 Cflags 一致）+ `bindirs=["bin"]`。
4. **R38**：构建产物含 JxrDecApp/JxrEncApp，软件级 commands.json 已声明。

## 测试事实（诚实记录）

- **上游测试套件：不存在（NO_UPSTREAM_TESTS）**。快照 107 个条目全量
  审计（2026-09-18）：Makefile 只有 all/clean/install（`make check`
  报 No rule to make target）；全树无 CMake/ctest；无 tests/ 目录；
  `-iname '*test*'` 仅命中 `jxrtestlib/`（BMP/TIF/PNM/HDR/YUV 文件
  I/O 支持库，编入 libjxrglue，名字里的 test 指测试图像文件 I/O，
  非测试套件）与 `bin/` 下上游误提交的 Windows .exe。上游验证方式
  是用 JxrDecApp/JxrEncApp 手工往返样例图像（MSVC 工程）。
- **test_package 消费者**（`consumer_roundtrip.c`，23 断言）：
  真实链接打包的 libjxrglue+libjpegxr，走完整公开 PK* API：
  PKCreateFactory/PKCreateCodecFactory → CreateStreamFromFilename →
  CreateCodec(IID_PKImageWmpEncode) → Initialize/SetPixelFormat/
  SetSize/SetResolution/WritePixels 编码 32x32 RGB 渐变 →
  CreateDecoderFromFile → GetSize/GetPixelFormat →
  PKFormatConverter::Copy 回读 → 逐字节近无损断言（容差 ≤3）+ 非退化
  断言。编码参数逐字段复刻上游 JxrEncApp 默认值（YUV_444/BD_LONG/
  FREQUENCY/OL_ONE/SB_ALL/QP=1）。
- **本机预验证（macOS arm64 原生 clang，补丁后源码）**：make 全绿；
  双工具 `--version` 退出 0；consumer_roundtrip 23/23 通过且
  maxdiff=0（QP=1 下该渐变图逐字节一致）。OHOS 侧以设备 W3 与 CI
  为准。
- CreateNewFrame 注意点：本快照 `PKImageEncode_CreateNewFrame_WMP`
  为 `WMP_errNotYetImplemented` 桩，裸 WritePixels 路径（HD Photo
  单帧样例范式）不经过它——消费者测试已按此路径编写并在本机验证。

## 已知限制

- 上游 bin/ 目录误提交的 Windows .exe（hdr2hdr.exe/imagecomp.exe）
  不参与构建，不打包。
- MSVC 工程（vc11/12/14）不参与构建。
- `make install`/pc 文件未走上游 python 生成路径（CI/设备无此需求，
  pkg-config 消费者可依 include/libjxr 布局自写 pc）。
- 纯静态库包：未声明 shared 选项——上游 `SHARED=1` 的 .so 规则无
  soname/版本化且链接规则不带 LDFLAGS，默认静态即上游形态；Conan 2.29
  对 library 类型强制要求 shared 选项，故 package_type 用 static-library
  （ada-bar-codes 等仓内先例）。
- 设备 W3 备注（三轮实测）：①make 必须串行——HMDFS 禁 mkfifo，GNU
  make 4.4 的 `-j` FIFO jobserver 直接失败（"jobserver mkfifo:
  Operation not permitted"）；②必须同源构建——`layout()` 里
  `folders.build="."`（aescrypt 先例），basic_layout 的 build-release/
  目录不含源码拷贝，make 报 "No targets specified and no makefile
  found"；③补丁在 source() 应用（build 阶段才 apply 会晚于源码就位）。
---

**编译结束**: 2026-09-18 02:03
**最终状态**: built
