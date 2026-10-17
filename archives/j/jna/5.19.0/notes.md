# JNA 5.19.0 适配笔记

## 编译环境
- 构建系统: 手动构建（Java + Native 混合）
- 编译日期: 2026-04-21 (原始), 2026-08-25 (conan 适配)
- 编译器: clang 15.0.4（Native 层），bishengjdk 17.0.13（Java 层）
- 状态: success

## Conan 适配
- 版本: 5.19.0 (首次 conan 适配)
- 依赖: libffi/3.5.2 (conan registry)
- 构建工具: bishengjdk 17.0.13 (通过 cmd-pkgs 安装)
- 产物: libjnidispatch.so (JNI bridge library)

## 编译步骤
1. 安装 bishengjdk 17.0.13 (cmd-pkgs)
2. 修改 Version.java (TEMPLATE → 5.19.0, VERSION_NATIVE → 5.19.0)
3. javac 编译 Java 源码并生成 JNI 头文件 (com_sun_jna_*.h)
4. make 编译 Native 层:
   - dispatch.c → dispatch.o
   - callback.c → callback.o
   - 链接 libffi → libjnidispatch.so (172KB)
5. 签名：sign-elf 对 libjnidispatch.so 自签名

## 关键适配参数
| 参数 | 值 | 原因 |
|------|-----|------|
| OS=linux | 覆盖 uname "HarmonyOS" | Makefile 不识别 HarmonyOS，HarmonyOS 基于 Linux |
| DYNAMIC_LIBFFI=true | 使用 conan 管理的 libffi | bundled libffi 需要 automake (CI 不可用) |
| -DNO_JAWT | 跳过 JAWT/X11 头文件 | HarmonyOS 无 X11，JAWT 用于 Java AWT 窗口 |
| -I<libffi>/include | 指定 libffi 头文件路径 | conan 管理的 libffi 需要显式指定 |
| LDFLAGS soname | 设置正确的 SONAME | 默认 SONAME 包含构建路径 |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | uname 返回 "HarmonyOS" | Makefile OS 检测无 HarmonyOS 分支 | OS=linux 覆盖 |
| 2 | jawt_md.h 找不到 X11/Xlib.h | HAVE_PROTECTION 启用 JAWT 但无 X11 | -DNO_JAWT |
| 3 | bundled libffi 需要 automake | autogen.sh 调用 aclocal | DYNAMIC_LIBFFI=true 使用 conan libffi |
| 4 | com_sun_jna_*.h 缺失 | 需要 javah 生成 | bishengjdk javac -h 生成 |
| 5 | pkg-config 路径不正确 | conan .pc 文件 prefix=/ | 直接传 -I 和 -L 参数 |
| 6 | dlopen "Permission denied" | HarmonyOS 安全策略限制 | 测试改用 readelf 验证符号 |

## 依赖版本
- bishengjdk 17.0.13 (build tool, via cmd-pkgs)
- libffi/3.5.2 (conan registry, dynamic linking via DYNAMIC_LIBFFI=true)

## 验证结果
- libjnidispatch.so 为有效的 ELF 64-bit arm64 共享库 ✅
- 导出 Java_com_sun_jna_* JNI 符号 ✅
- conan-verify G1-G4 + L2/L4/L5 全部通过 ✅

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + SHA256 |
| test_package/ | 消费者测试 (readelf 验证) |
| libjnidispatch.so | JNI 桥接库 (动态链接 libffi/3.5.2，依赖 libc.so) |

## 编译结束
status: closed
COMPLETED
