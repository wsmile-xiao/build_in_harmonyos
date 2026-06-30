# freac 1.1.7 编译笔记

## 编译概况
- **构建系统**: custom Makefile（类似 smooth/boca）
- **依赖**: smooth 0.9.10, boca 1.0.7, GTK+3.24.43, pango, epoxy, fribidi, zlib, libjpeg-turbo, libpng, libxml2, libcurl, libbz2, libcpuid, iconv
- **编译状态**: 编译成功，运行时依赖 GTK+3/pango/epoxy（库链运行验证因缺少动态库路径而失败，非致命，GUI启动需GTK+3生态完整）
- **主要补丁**:
  1. 0001-Makefile.patch - Makefile --shared → -shared（clang++ linker兼容性）
  2. 0002-Makefile-commands.patch - Makefile-commands --shared → -shared（clang++ linker兼容性）
  3. 0003-Makefile-options.patch - Makefile-options HarmonyOS 平台检测 + LD=clang++ override + 系统库路径

## 关键发现
1. freac 使用自定义 Makefile 构建系统（非 autotools/cmake），与 smooth/boca 结构相同
2. LD 必须覆盖为 clang++（ld.lld 无法正确链接共享库）
3. --shared 选项必须改为 -shared（clang++ 链接器兼容性）
4. freac 1.1.7 源码已包含 HarmonyOS 平台检测（`ifeq ($(UNAME),HarmonyOS) BUILD_LINUX = True`）
5. 需要手动安装 boca.h 和 support/ 头文件（boca install 不包含这些）
6. 运行时依赖 GTK+3 生态链（pango, epoxy 等）

## 编译命令
```bash
cd /storage/Users/currentUser/tmp/builds/freac-1.1.7.work
make config=release prefix=/storage/Users/currentUser/usr/local
```

**编译开始**: 2026-05-30 17:15
**编译结束**: 2026-05-30 17:16
**最终状态**: built
---

**编译结束**: 2026-05-30 17:31
**最终状态**: built
