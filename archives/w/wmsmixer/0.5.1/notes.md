# wmsmixer 0.5.1 适配笔记

## 编译环境
- 构建系统: custom（上游 Imakefile/xmkmf，环境无 imake，改为直接 clang++ 编译）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built

## 编译步骤

1. 源码获取：dockapps.net 提供 wmsmixer-0.5.1.tar.gz（上游官方 hibernaculum.net 当前 DNS 不可达；
   dockapps.net 为 Window Maker dockapps 官方站点）。sha256=eee60a40ba92e4c2c9a038c6e51cd3bd62b24b38a096d091dc60dfd26f0c5daa。
2. 依赖注入：conan install libx11/6.4.0 + libxpm/3.5.17 + libxext/6.4.0.1（ohpcd 制品仓，均已发布；
   X11/X.h 等协议头由 xorgproto 传递提供）。
3. 编译命令（手动验证通过，exit=0，arm64 ELF 产物）：
   ```
   clang++ -O2 -fPIC -std=c++17 \
     -I<libx11/include> -I<libxpm/include> -I<libxext/include> -I<xorgproto/include> \
     wmsmixer.cc -o wmsmixer \
     -L<libx11/lib> -L<libxpm/lib> -L<libxext/lib> \
     -lX11 -lXpm -lXext
   ```
   注：链接器 lld 运行时依赖 SDK llvm/lib 下的 libxml2.so.16，编译前须注入
   `LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib`。
4. 产物校验：ELF Type=DYN (PIE)、Machine=AArch64；`wmsmixer --version` 在 X 连接前打印
   "wmsmixer version 0.5.1" 并 exit(0)（无显示环境可端到端运行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Imakefile 用 xmkmf/imake 生成 Makefile，本机与 CI 均无 imake | imake 为 X11 老工具链，OHOS 环境无该工具 | conanfile.py build() 改为直接 clang++ 编译 wmsmixer.cc（单一源文件 + mixctl.h 头文件），链接 -lX11 -lXpm -lXext |
| 2 | 上游 Imakefile 中 `CC = c++ -m32`（32 位编译标志） | 2003 年老代码硬编码 32 位 | 直接编译方案不使用该标志，arm64 下自然规避 |
| 3 | 手动编译报 X11/X.h not found | X11 协议头（X.h/Xproto.h）由 xorgproto 包提供，不在 libx11 包 | 注入 xorgproto 的 include 路径（conan 依赖传递自动提供） |
| 4 | 链接报 xmlFree symbol not found / lld 无法定位 libxml2 | OHOS SDK 的 lld 二进制依赖 llvm/lib 下 libxml2.so.16，无 RUNPATH | 编译前注入 LD_LIBRARY_PATH 指向 llvm/lib（同 asmix CI #30003 根因） |
| 5 | mixctl.h 依赖 OSS 音频 ioctl（linux/soundcard.h） | 老 OSS 混音器接口 | OHOS sysroot 提供 linux/soundcard.h，编译通过；运行期需 /dev/mixer 设备（GUI 使用场景，不影响编译/打包） |

## 源码修改

无补丁（patches/ 为空）。构建方式在 conanfile.py build() 中替代上游 imake 流程。

## 依赖版本

- libx11/6.4.0（Xlib/Xutil 头文件、-lX11）
- libxpm/3.5.17（X11/xpm.h、-lXpm）
- libxext/6.4.0.1（X11/extensions/shape.h、-lXext，XShapeCombineMask 使用）
- 传递依赖：xorgproto/2025.1（X11/X.h、X11/Xproto.h 协议头）、libxcb/1.17.0.1、libxau、libxdmcp、xtrans 等

## 验证结果

```bash
# 手动编译验证（2026-09-29）
clang++ -O2 -fPIC -std=c++17 ... wmsmixer.cc -o wmsmixer ... -lX11 -lXpm -lXext
# exit=0，产物 arm64 ELF（Type=DYN PIE, Machine=AArch64）

# test_package 消费者测试（test.c）
# 1) 产物 arm64 ELF 校验（magic + e_machine）
# 2) 端到端执行 wmsmixer --version，验证退出码 0 且输出含 "0.5.1"
```

## 注意事项

- wmsmixer 是 X11 GUI dockapp，OHOS 无显示环境，运行时需要 X server 与 /dev/mixer 设备；
  本适配保证编译、打包、命令行版本/帮助功能可用（--version/--help 在 X 连接前处理）。
- 上游无测试套件（tarball 内无 tests/，Imakefile 无 check 目标），test_package 补充了
  产物 ELF 校验 + --version 端到端用例作为真实消费者测试。
---

**编译结束**: 2026-09-29 23:45
**最终状态**: built
