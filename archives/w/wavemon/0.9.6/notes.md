# wavemon 0.9.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖: libnl 3.12.0 (预编译包), ncurses (静态库已安装)
2. init-build: ohc-run.py init-build wavemon 0.9.6
3. 修改源码（见下方修改清单）
4. autoreconf -fi 生成configure
5. sed -i 's/umask 077/umask 022/g' configure (E011修复)
6. sed -i 's/umask 077/umask 022/g' config/config.guess (E011修复)
7. ./configure --prefix=$DEFAULT_PREFIX CPPFLAGS="-I$DEFAULT_PREFIX/include -I$DEFAULT_PREFIX/include/ncurses" PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
8. unset CFLAGS; unset LDFLAGS; unset CPPFLAGS; make -j1 (环境变量会覆盖Makefile的?=默认值)
9. make install DESTDIR=$TEST_PREFIX
10. make install (本地安装)
11. verify → package → finish

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ncurses.h not found | ncurses.h在ncurses/子目录，需额外-I路径 | CPPFLAGS添加-I$DEFAULT_PREFIX/include/ncurses |
| 2 | config.status Permission denied (E011) | HMDFS的umask 077导致临时目录不可写 | sed umask 077→umask 022 in configure & config.guess |
| 3 | config.guess unable to guess system type | uname -s返回"HarmonyOS"，2023-08-22版不识别 | 添加HarmonyOS到$UNAME_SYSTEM case, aarch64:HarmonyOS映射 |
| 4 | config.sub OS 'ohos' not recognized | config.sub缺少ohos识别 | 在config.sub添加ohos*和linux-ohos*-模式 |
| 5 | linux/if.h sockaddr_storage redefinition | linux/if.h与sys/socket.h冲突(E007类似) | configure.ac改linux/if.h为可选,utils.c用#ifdef __OHOS__改用net/if.h |
| 6 | netlink/netlink.h→linux/socket.h redefinition | 同上sockaddr_storage问题 | iw_nl80211.h添加_UAPI_LINUX_SOCKET_H guard + __kernel_sa_family_t定义 |
| 7 | pthread_cancel not available (OHOS/musl) | musl不完全实现pthread取消机制 | iw_if.h添加OHOS守卫宏(pthread_cancel=no-op, pthread_setcancelstate=inline) |
| 8 | WACS_HLINE/WACS_* not defined | ncursesw头文件缺少宽字符API | wavemon.h: #undef HAVE_LIBNCURSESW on OHOS, 用curses.h + KEY_F宏 |
| 9 | KEY_F not defined | curses.h缺少KEY_F宏 | wavemon.h: #define KEY_F0/#define KEY_F(n) |

## 源码修改清单

| 文件 | 原因 | 方式 |
|------|------|------|
| configure.ac | linux/if.h OHOS兼容 | 改为可选检查+net/if.h替代 |
| configure | E011 umask修复 | sed umask 077→022 |
| config/config.guess | OHOS平台识别 | sed umask + 添加aarch64:HarmonyOS case |
| config/config.sub | OHOS OS识别 | 添加ohos* + linux-ohos* |
| utils.c | linux/if.h OHOS替代 | #ifdef __OHOS__ 用net/if.h |
| iw_nl80211.h | linux/socket.h冲突 | #ifdef __OHOS__ skip + typedef __kernel_sa_family_t |
| iw_if.h | pthread_cancel缺失 | OHOS守卫宏 |
| lhist_scr.c | WACS_HLINE缺失 | #ifdef HAVE_LIBNCURSESW / __OHOS__用ACS_HLINE |
| wavemon.h | ncursesw宽字符API缺失 | #undef HAVE_LIBNCURSESW + curses.h + KEY_F |

## 构建提示

- autoreconf后需手动sed修复umask (E011): sed -i 's/umask 077/umask 022/g' configure config/config.guess
- make时需unset环境变量CFLAGS/LDFLAGS/CPPFLAGS（避免覆盖Makefile ?=默认值）
- configure需CPPFLAGS="-I$DEFAULT_PREFIX/include -I$DEFAULT_PREFIX/include/ncurses"（ncurses.h在子目录）

## 依赖版本

- ncurses: 静态库 (--without-shared)
- libnl 3.12.0: 预编译包 (含cli/genl/route/nf/xfrm组件)
- libcap: 系统库

## 验证结果

wavemon --version → wavemon 0.9.6
wavemon --help → 正确输出使用帮助

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wavemon-0.9.6-ohos-aarch64.tar.gz | 1481KB | 预编译包 |
| wavemon | 338KB | ELF aarch64动态链接 |

## 注意事项

- wavemon需要root权限和无线网络接口才能完整运行
- HarmonyOS缺少无线接口，无法进行完整运行测试
- 所有源码修改使用#ifdef __OHOS__守卫，不影响非OHOS平台
---

**编译结束**: 2026-06-02 16:00
**最终状态**: published
