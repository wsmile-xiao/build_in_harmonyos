# DRAFT — tmate 2.4.0 OHOS Autotools 探测名对齐 + 头文件检查顺序

> 状态: 草稿(仅服务 tmate 2.4.0, 待查重/提升)。知识库查重结论见文末。

## 真实问题(本轮 tmate 2.4.0 适配实际命中)

1. **pkg-config 探测名不一致**: ohpcd 配方声明的 pkg-config 名与上游 `configure.ac`
   探测名不同,configure 阶段直接 `AC_MSG_ERROR`:
   - msgpack-c/7.0.0 配方 `pkg_config_name="msgpack-c"`,上游探测 `msgpack >= 1.1.0`
   - ncurses/6.6 配方 `pkg_config_name="ncursesw"`,上游探测 `ncurses`
   - (libevent/2.1.13 与 libssh/0.11.4 的 `pkg_config_name` 与上游探测名一致,无需改)

2. **头文件检查早于依赖 -I 注入**: `configure.ac` 中
   `AC_CHECK_HEADERS(curses.h ncurses.h term.h ...)` 位于
   `PKG_CHECK_MODULES(LIBNCURSES, ncursesw)` **之前**;此时 ncurses 的 `-I include`
   尚未进入 CPPFLAGS → 头文件检查全部失败 → `HAVE_CURSES_H/HAVE_NCURSES_H/HAVE_TERM_H`
   未定义 → `tty-term.c` 的 `#if defined(HAVE_CURSES_H) #include <curses.h>` 分支不生效
   → 编译报 `use of undeclared identifier 'OK'`(`setupterm(...) != OK`)。

3. **GitHub tag 归档无预生成 configure**: `tmate-2.4.0.tar.gz` 无 configure/Makefile.in/
   aclocal.m4/aux 脚本,须先在主机 autogen(aclocal+automake+autoreconf)再以新文件
   patch 落盘(dhcpstarv r44 同款模式);config.guess 需含 HarmonyOS 探测块(E007 已覆盖)。

## 修复(本轮真实实施,全部在 archives/t/tmate/2.4.0/** 内)

`patches/0001-configure-ac-probes.patch`:
- `msgpack >= 1.1.0` → `msgpack-c >= 1.1.0`
- `ncurses` → `ncursesw`
- 将整个 `AC_CHECK_HEADERS(...)` 块后移到 libevent/ncurses/msgpack/libssh 四个
  `PKG_CHECK_MODULES` 之后,使依赖 `-I` 先注入 CPPFLAGS
- 重新 autogen 并把生成的 configure/Makefile.in/aclocal.m4/etc/* 以新文件 patch
  落盘(0002-0010),0003 config.guess 含 HarmonyOS 探测块

`test_package/conanfile.py`: 运行 `tmate -V` 时使用 `env="conanrun"` 提供依赖共享库
运行时路径(libevent.so 为 ohpcd 共享构建,裸 subprocess 运行时符号无法重定位)。

## 复用步骤

1. 读上游 `configure.ac`,提取全部 `PKG_CHECK_MODULES` 探测名。
2. 逐个与 ohpcd 依赖配方的 `pkg_config_name` 比对,不一致者 patch 探测名。
3. 检查 `AC_CHECK_HEADERS` 是否早于依赖 `PKG_CHECK_MODULES`;若是,把头文件检查块
   后移到 pkg-config 检查之后。
4. 主机 autogen 预生成产物并以新文件 patch 落盘;config.guess 加 HarmonyOS 探测。
5. test_package 用 `env="conanrun"` 运行冒烟。

## 验证

- `conan create`(iter3): PASS, test_package 冒烟 `tmate 2.4.0`
- `conan-verify`: G0-G4 全 PASS, verdict PASS
- finish: W2/W3/W4 本地门禁通过

## 知识库查重结论

- **E007**(config.guess/HarmonyOS/autoconf): 本轮 config.guess 问题与其重叠,复用其
  HarmonyOS 探测块思路;本草稿聚焦探测名对齐 + 头文件检查顺序,非重复条目。
- **E277**(vendored 依赖内联构建): 其中「tmate 2.4.0 | libssh + msgpack-c + mbedtls +
  ncurses | 内联构建四个依赖静态库」与真实 tmate 2.4.0 源码**不符** —— 真实依赖为
  外部 pkg-config REQUIRED 的 libevent/ncurses/msgpack/libssh(含 libevent 而非
  mbedtls,非 vendored 内联),且本轮强制依赖全部在 ohpcd 可消费、无需内联构建。
  E277 的 tmate 案例描述不可原样复用,需修正后才可作 B 依据。
- **E175**(HMDFS autoreconf-regenerate): 本轮未在 HMDFS 上触发 autoreconf 写入问题
  (预生成 configure 走 patch),与本草稿正交。
- 知识库无「pkg-config 探测名对齐」与「AC_CHECK_HEADERS 先于依赖 -I 注入」的既有条目,
  本草稿为新增候选。

## 关联条目

- 相关: E007(config.guess HarmonyOS)、E175(HMDFS autoreconf)、E277(vendored,其 tmate 案例待修正)
