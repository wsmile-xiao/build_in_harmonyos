# uclibc 1.0.54 适配笔记

## 编译环境
- 构建系统: makefile（Kconfig + GNU make，类似 Linux 内核）
- 编译日期: 2026-09-19（真机 shadow CI 通过）
- 编译器: clang 15.0.4（aarch64-linux-ohos，CI 提供）
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（conan create + test_package 成功）

## W0 依赖检查

- 依赖数量: 0（无 Conan 运行时/构建/测试依赖，uClibc-ng 自包含）
- 工具链层面依赖: GNU make、宿主 C 编译器（HOSTCC，生成 conf/unifdef 宿主工具）、
  目标交叉编译器（OHOS clang + llvm binutils）、目标内核头文件（OHOS SDK sysroot）
- 测试依赖: 无（上游官方测试在独立仓库 uClibc-ng-test，不随源码 tarball 发布）
- 是否需要拆分依赖适配: 否

## W1 源码与构建系统分析

- 类型: 纯 C，Kconfig + GNU make（非 autotools/CMake/Meson）
- aarch64 支持存在，但**无预置 aarch64 defconfig**，用 `KCONFIG_ALLCONFIG` 片段 + `allnoconfig` 生成 `.config`
- 产物: libc.so/libc.a、ld-uClibc-*.so、crt*.o 启动文件、整套 C 头文件、libpthread/libm 等
- 作为 libc 本体，与 OHOS musl sysroot 天然冲突；消费者需 `-nostdinc/-nostdlib` 方式使用
- 许可证: LGPL-2.1

## 构建流程

- source(): Bootlin 镜像 tarball（官方站 522/525 不可用），sha256 本机核验
- build(): 探测 OHOS SDK sysroot（`clang -print-resource-dir` 上溯）→ 源码预处理（见下）→
  `make KCONFIG_ALLCONFIG=<片段> ARCH=aarch64 allnoconfig` → `make all`（命令行覆盖
  CC/AR/NM/OBJDUMP/STRIPTOOL/LD/HOSTCC + --target/--sysroot + TMPDIR + LN wrapper）
- package(): `make install`（复用 build() 工具链变量）

## 源码适配（conanfile.py 预处理，等价 patch）

| 文件 | 改动 | 原因 |
|---|---|---|
| Makefile.in | 脚本调用加 `$(SHELL)` | HMDFS 上脚本无 other 执行位，直接执行 Permission denied |
| Makerules（ln wrapper） | `ln -fs` 用 cp 模拟 | HMDFS 软链接被拒；cp 拼 `dirname(dst)/src` 保路径语义 |
| extra/scripts/gen-as-const.awk | 裸 `@@@name@@@` asm 改 `.ascii`+`%c0` | clang 前端解析 asm 模板失败（gcc 惰性原样输出） |
| Rules.mak | 去 `-nostdinc`、删空 `-I$(KERNEL_HEADERS)` | 让 clang `--sysroot` 默认 multilib 路径解析内核头文件 |
| ldso/ldso/Makefile.in | `ln -sf` → `cp -f` | ldso 向后兼容链接同目录软链接 |
| libc/unistd/getopt-susv3.c | 补 `#define _(x) (x)` | uClibc libintl.h 未定义 gettext 简写 `_`，clang 报 int→pointer |
| libpthread/nptl/allocatestack.c | GCC 嵌套函数 `check_list` 提取为静态函数 | clang 不支持 GCC 嵌套函数 |
| librt/Makefile.in | ADVANCED 过滤补 `clock_gettime.c` | REALTIME=y 时 common/librt 双份 clock_gettime 重复归档 |
| librt/dso_handle.c | `__dso_handle` 加 `weak` | 与 clang crtbegin.o 的强符号冲突 |
| libc/misc/internals/h_errno.c + netdb.h | 去 TLS alias | clang emutls 不生成 TLS alias 的 `__emutls_v.` 符号 |
| libc/Makefile.in | `--allow-shlib-undefined` | lld 对 hidden undefined 比 GNU ld 严格 |
| ldso/libdl/libdl.c | include `dl-tls.c` | 让 `_dl_allocate_static_tls` 等 TLS 函数在 libc.so 内定义 |
| ldso/libdl/Makefile.in | `dl-tlsdesc.oS` 加进 libdl-so-y | `_dl_tlsdesc_return`（汇编）归档进 libc_so.a |
| libc/sysdeps/linux/aarch64/crt1.S | 非 `L_Scrt1` 分支显式清零 x5（rtld_fini） | OHOS 内核静态入口不清理 x0，`__uClibc_fini` 对垃圾地址 br 触发 SIGSEGV |

## 遇到的问题与解决方案（25 次 shadow CI 迭代）

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | 官方站 522/525 | downloads.uclibc-ng.org 超时 | Bootlin 镜像 + sha256 本机核验 |
| 2 | aarch64 无 defconfig | uClibc 未内置 aarch64 defconfig | KCONFIG_ALLCONFIG + allnoconfig |
| 3 | conf 宿主工具用 gcc 失败 | 设备无 gcc，HOSTCC 默认 gcc | `HOSTCC=clang` |
| 4 | `/tmp` 只读 | 鸿蒙 PC /tmp 只读 | `TMPDIR=<build>/.tmp` |
| 5 | conf-header.sh 权限 | HMDFS 脚本无执行位 | Makefile 脚本调用加 `$(SHELL)` |
| 6 | 软链接被拒 | HMDFS 不支持 symlink | ln wrapper 用 cp 模拟 |
| 7 | 内核头文件找不到 | OHOS sysroot multilib 分层 | CC 注入 `--target --sysroot` + 去 `-nostdinc` |
| 8 | gen-as-const gcc 裸 asm | clang 解析 asm 模板失败 | `.ascii` + `%c0` |
| 9 | 工具链路径缺失 | profile 只给 clang，ar/nm 裸名 | llvm 绝对路径 + GNU strip |
| 10 | gettext `_` 宏缺失 | uClibc libintl.h 无 `_` | 补 identity 宏 |
| 11 | GCC 嵌套函数 | clang 不支持 nested function | 提取静态函数 |
| 12 | strip relocation 符号过严 | llvm-objcopy 比 GNU strip 严 | 换 GNU strip |
| 13 | `__dso_handle` 重复 | clang crtbegin 提供强符号 | dso_handle.c 加 weak |
| 14 | clock_gettime 重复归档 | REALTIME 下 common/librt 双份 | librt ADVANCED 过滤 |
| 15 | `__GI_dup3` undefined | aarch64 用 dup3，LINUX_SPECIFIC 未开 | `UCLIBC_LINUX_SPECIFIC=y` |
| 16 | `__libc_h_errno` undefined | clang emutls 不支持 TLS alias | 去 alias |
| 17 | package() 重编译用 gcc | install 未传工具链变量 | package 复用 build 工具链 |
| 18 | `_dl_*` TLS 符号 undefined | lld 对 hidden undefined 严格 | include dl-tls.c + dl-tlsdesc.oS 归档 |
| 19 | 静态链接程序 exit 段错误（rc=139） | OHOS 内核静态入口 x0 未清零，crt1.S 把 x0 当 rtld_fini 传给 `__uClibc_main`，退出时 `__uClibc_fini` 对该垃圾地址 `br` | crt1.S 非 `L_Scrt1` 分支清零 x5（rtld_fini=NULL，仅 Scrt1 由 ld.so 传入） |
| 20 | 官方 CI libc.so 链接 undefined（`_dl_phnum` 等） | Rules.mak 硬编码 `-Wl,-z,defs`，lld 严格报 undefined，`--allow-shlib-undefined` 无法覆盖 | 去掉 `-z defs`，undefined 交由运行时解析 |
| 21 | 官方 CI 的 `.os`/`.oS` 的 `-DSHARED` 分配颠倒 | 官方 CI 部分 worker 文件系统对 `.os`/`.oS` 大小写不敏感，二者互相覆盖 | `.oS` 后缀全局改名 `.oshared`（与 `.os` 不再相似），保留 `.oshared` 的 `-DSHARED` |
| 22 | test_package 静态链接时 lld 报 `xmlFreeDoc: symbol not found` | OHOS SDK 的 lld 依赖 llvm/lib 的 libxml2.so（无 RUNPATH），部分 worker 的 buildenv LD_LIBRARY_PATH 未传递到 subprocess | test_package 从 resource-dir 上溯到 llvm/lib 显式前置 LD_LIBRARY_PATH |
| 23 | 官方 CI ldso.c 报 `-Wint-conversion`（init_tls 隐式声明） | ldso.c 调用 init_tls() 但无前向声明（声明在 dl-tls.c 的 `#ifdef SHARED`），隐式 int 返回值赋给 void* | ldso.c 补 `extern void *init_tls(void)` 前向声明 |
| 24 | `.oS`→`.oshared` 改名后 duplicate symbol（fork 等） | 改名过滤遗漏 `Makefile.commonarch`（含 `.o=.oS`），部分对象仍编译为 `.oS` 与 `.oshared` 重复归档 | 过滤改为 `fn.startswith("Makefile")` 全量覆盖 |

## 依赖版本

- 无 conan 依赖（uClibc-ng 零外部依赖，自包含 C 标准库）

## 验证结果

- 源码归档: 1986084 字节，sha256 d1ecf65c…43ff2，xz magic + 解包核验通过
- 真机 shadow CI: **conan create + test_package 通过**（第 25 次）
  - L0_RESULT=pass、L1_RESULT=pass（test_package 执行）、L4_RESULT=pass、L5_RESULT=pass（lib/ 有内容）
  - L2_RESULT=skip（libc 无 bin/ 目录，正常）
  - 上游测试（uclibc-ng-test@996f404，静态链接真机运行）：`compiled 5 upstream uClibc-ng tests`，`uclibc upstream tests: 5/5 passed`
  - L1e 破坏性负测试通过（test 真实依赖 uclibc）
- 官方 CI（PR #11071）: **构建 #51206 校验通过**
  - Conan test_package 通过、L0 门禁（结构完整性）通过、L1 门禁（测试执行验证）通过
- 本机构建: 未执行（本机无 OHOS 交叉工具链与 Conan）

---

**编译结束**: 2026-09-19
**最终状态**: built
