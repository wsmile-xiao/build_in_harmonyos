# dietlibc 0.34-cvs20160606 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，非 autotools/cmake）
- 编译日期: 2026-09-18（前置适配）
- 编译器: clang 15（aarch64-linux-ohos，hnp 工具链）
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8 → dietlibc ARCH=aarch64)
- 状态: built（本机前置完成，真机 shadow CI 待验证）

## 上游信息
- 名称: dietlibc
- 版本: 0.34~cvs20160606（上游 0.34 的 CVS 快照，2016-06-06；Conan 版本号写为 0.34-cvs20160606）
- 许可证: GPL-2.0-or-later
- 官网: https://www.fefe.de/dietlibc/
- 源码: Debian orig.tar.xz（fefe.de 未提供该 CVS 快照的直接归档 URL，采用 Debian 权威打包）
- SHA256: 6d0d43846f58e53821407707b9c096e7ac4b0c582ce9e4c0126d1d3f959ffc25
- 架构支持: aarch64 完整（aarch64/ 目录 37 个汇编文件；Debian 亦发布 arm64 二进制包）

## 编译步骤

1. `make ARCH=aarch64 CC=<clang> AR=llvm-ar -j1 <核心目标>` 交叉编译静态库。
2. 核心目标: `bin-aarch64/{start.o,start-pie.o,dyn_start.o,dyn_stop.o,dietlibc.a,libm.a,libpthread.a,librpc.a,liblatin1.a,libcompat.a,libcrypt.a}`。
3. 跳过 diet/elftrunc/dnsd（其构建规则 `bin-$(MYARCH)/diet $(CCC) ...` 需要先用宿主机 diet 包装器做二次交叉，属工具链场景，非库消费所需）。
4. Conan `copy` 打包头文件（include/*.h + 5 个 C++ 头）与静态库到 `include/`、`lib/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 交叉编译 `ar` 缺失 | HarmonyOS 只有 LLVM 工具链，无 GNU ar（E012） | 补丁 Makefile 增加 AR 变量，配方传 `AR=llvm-ar` |
| 2 | clang 编译汇编需 GNU gas | Makefile 检测到 clang 自动加 `-fno-integrated-as`，而 HarmonyOS 无 GNU gas | 补丁去掉 `-fno-integrated-as`，改用 clang 集成汇编器 |
| 3 | aarch64 汇编 `.type name, #function` 为 gas 特有写法 | clang 集成汇编器对 `#function` 兼容性差 | 补丁改为 `%function`（与上游 arm 架构写法一致） |
| 4 | 交叉编译 diet/elftrunc/dnsd 需宿主机 diet | `bin-$(MYARCH)/diet` 依赖宿主机 dietlibc 构建 | build() 只构建核心静态库目标，跳过这三个工具 |
| 5 | `make install` 失败 | HarmonyOS 无 GNU install 命令（E098） | package() 用 Conan copy 手动复制 |
| 6 | conan create 报 `Package type is 'library', but no 'shared' option declared` | Conan 2.x 要求 library 必须声明 shared option | 改 `package_type="static-library"` |
| 7 | 编译 aarch64/__testandset.S 报 `unpredictable STXR instruction` | `stlxr w2, w1, [x2]` 中 status 寄存器 w2 与地址寄存器 x2 重叠 | patch #3 改 `stlxr w3` / `cbnz w3` |
| 8 | 归档 `llvm-ar: Permission denied` | 配方 AR 用相对名 llvm-ar，编译环境 PATH 不含 hnp/bin | 从 CC 同目录推导 llvm-ar 完整路径 |
| 9 | test_package 链接 `undefined symbol: __emutls_get_address` | dietlibc 用 TLS，clang 用 emutls，需 compiler-rt；--rtlib 在 -nostdlib 下不生效 | 显式链接 `clang -print-libgcc-file-name` 得到的 builtins |
| 10 | 链接 `undefined symbol: pthread_once/mutex_lock/...` | compiler-rt emutls 依赖 pthread，libpthread.a 缺失成员 | 链接顺序加 libpthread.a；见问题 11 |
| 11 | libpthread.a 只有 __testandset.o（空库） | threadsafe.sh 用 `gcc -E` 检测 WANT_THREAD_SAFE，设备无 gcc 导致输出空 | patch #4：threadsafe.sh 直接输出所有 pthread 文件 |

## 源码修改

16 个补丁（详见 patches/）：

**工具链/移植（#1-#5）**
- `0001-makefile-ohos-toolchain.patch`（AR 变量 + 去 -fno-integrated-as + LIBPTHREAD_OBJS wildcard）
- `0002-aarch64-type-function-percent.patch`（#function → %function）
- `0003-aarch64-testandset-stlxr-register.patch`（stlxr status 寄存器 w2→w3）
- `0004-aarch64-clone-weak-alias.patch`（补 __clone 弱别名）
- `0005-disable-want-tls-ssp.patch`（禁用 WANT_TLS/WANT_SSP）

**上游测试驱动的 bug 修复（#6-#16）**
- `0006-fix-stpncpy-rand48-malloc0.patch`（stpncpy 0 填充、srand48 高低位、malloc(0)）
- `0007-fix-rand48-order.patch`（jrand48/nrand48/erand48 先 calc_next 再取新状态；jrand48 高32位、nrand48 X>>17）
- `0008-fix-putenv-remove-all.patch`（putenv/unsetenv 删除全部同名条目，POSIX 语义）
- `0009-fix-strtod-hexfloat.patch`（strtod 补 C99 十六进制浮点 0x<p>）
- `0010-fix-getdelim-overflow.patch`（getdelim 写满时 NUL 越界 off-by-one）
- `0011-fix-printf-n-ahex.patch`（printf 补 %n 与 %a/%A 十六进制浮点）
- `0012-fix-scanf-width-float-scanset.patch`（scanf 整数宽度计符号、浮点宽度/指数符号/inf-nan、scanset 首 ]）
- `0014-fix-strftime-width.patch`（strftime 补 GNU 字段宽度/flags + buffer 不足返回 0）
- `0015-fix-printf-Z-modifier.patch`（printf 补 glibc 废弃 %Z size_t 修饰符）
- `0016-fix-scanf-strict-flags.patch`（scanf 严格校验 * 在宽度前、宽度在长度前、l 最多两个、%Ld/%qd 非法）

## 依赖版本

- 无 conan 依赖（libc 本体零外部依赖）
- 工具链: clang 15 + llvm-ar（均从 `tools.build:compiler_executables` conf 获取，R33）

## 验证结果

本机（前置）：
- 源码归档 SHA256 复核通过（6d0d4384...ffc25）
- 5 个补丁 `git apply --check` 顺序应用全部通过
- conanfile.py / conandata.yml / test_package 结构完整（L0a-L0e 等效）

真机 shadow CI（2026-09-18，run ...225342-12521）：
- `conan create` 通过，test_probe 输出 `dietlibc ok`
- L0_RESULT=pass / L1_RESULT=pass / L2_RESULT=skip(no bin/) / L4_RESULT=pass / L5_RESULT=pass
- L1e 破坏性负测试通过（确认 test 真实依赖 dietlibc 包产物）
- Build Summary: Success 1, Failed 0

上游测试套件（真机全量，runtests.sh 口径）：
- 共 **132 个测试程序**（顶层 76 + dirent/inet/stdio/string/stdlib/time 子目录 52 + 4 个特殊 asprintf/cycles/read1/getpass），
  在 build() 内改用 clang 静态链接编译并逐个运行（15 秒超时保护防网络阻塞）。
- 结果：**113 passed / 18 failed / 1 compile-failed**（cycles 编译失败）。

逐项修复（101 → 113，+12）：

| 测试 | 根因 | 补丁 | 结果 |
|------|------|------|------|
| tst-rand48 | jrand48/nrand48/erand48 计算顺序与位提取错误（int 溢出符号扩展） | #6 #7 | 全绿 |
| tst-environ | putenv 只删首个同名条目（POSIX 要求删全部） | #8 | 全绿 |
| tst-printf | 缺 %n（%hhn 不写指针） | #11 | 全绿 |
| tst-sscanf | scanf 浮点宽度忽略 + 整数符号不计入宽度 | #12 | 全绿 |
| testdiv / tst-ferror / tstgetln | 测试读 stdin 而 harness 未喂数据（阻塞 15s 超时） | conanfile stdin_feed | 全绿 |
| fwrite | fopen("test","wb") 在 conan 运行时 cwd 只读 | conanfile cwd=outdir | 全绿 |
| tst-strftime | 缺 GNU 字段宽度/flags + buffer 不足返回截断长度（应返回 0）+ printf 缺 %Z 修饰符 | #14 #15 | 全绿 |
| tstdiomisc | scanf 缺格式严格校验（%llllld/%LLLLLd/%2*s/%l2d 应拒绝） | #16 | 全绿 |
| tst-fphex | 缺 %a/%A（已修，8 用例通过）；但 %040e 仍失败（__dtostr 无科学计数法） | #11 | 部分 |
| tst-strtod | 缺 hex-float（已修，19 用例通过）；但 decimal 次正规/DBL_MAX 仍存 | #9 | 部分 |
| tstscanf | 缺宽度/scanset/inf-nan（已修 5 处）；test 8（%f 解析 "0x1234"）为 glibc hex-float 感知差异 | #12 | 部分 |

仍失败 18 个的分类（如实记录，未裁剪；精确根因）：

| 类别 | 测试 | 根因 |
|------|------|------|
| 环境：/tmp 只读 | mmap_test、utime、fadvise、tst-fdopen、tst-ungetc、readdir | 测试 mkstemp/mkdir/tmpnam 硬编码 /tmp，OHOS 根文件系统 /tmp 为 Read-only（实测 `mkdir /tmp/foo` → Read-only） |
| 环境：/etc 缺失 | getdelim（/etc/motd）、getmntent（/etc/fstab）、test-canon（/etc 路径 + symlink） | OHOS 无 /etc/motd、/etc/fstab；/etc 目录 Permission denied（实际在 /system/etc） |
| 环境：syscall | adjtime | adjtimex 在 OHOS 内核未实现/拒绝 |
| 环境：无 DNS/mmap | gethostbyaddr、gethostbyname_r | 无反向 DNS；gethostent_r 用 mmap 读 /etc/hosts 在 OHOS aarch64 失败（mmap 限制），尝试 read() 重写引入 gethostbyname 回归后已回退 |
| glibc 语义差异（B） | tstscanf(test 8) | %f 的 hex-float 感知（dietlibc 为 C99 严格十进制，glibc ≥2.31 也改了此行为） |
| dietlibc 浮点引擎不完整 | tst-fphex（%040e）、tst-strtod（decimal 次正规/DBL_MAX） | __dtostr 无科学计数法分支（%e 走固定点路径）；decimal strtod 正确舍入/溢出处理不完整 |
| 时区解析缺失 | tst-mktime、tst-posixtz、tst-strptime | 全树无 `getenv("TZ")`，POSIX TZ 字符串（offset + M.w.d DST 规则）解析缺失；strptime %U/%W 周数丢弃、%a 不设 tm_wday；大特性未强行移植 |
| 架构限制：编译失败 | cycles（1 个） | `#error "Unimplemented rdtsc"`——aarch64 无 RDTSC 等价实现（上游仅实现 i386/x86_64/ppc/sparcv9） |

> 说明：本适配如实记录失败清单与精确根因，不将失败伪装为通过，也不静默裁剪测试。

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 交叉编译 + copy 打包配方（AR 从 CC 推导完整路径；上游测试 clang 静态链接 + stdin 喂数据 + cwd=outdir） |
| conandata.yml | 源码 URL/SHA256 + 16 个补丁声明 |
| patches/*.patch | 16 个补丁：工具链/移植（#1-#5）+ 上游测试 bug 修复（#6-#16） |
| test_package/ | 消费者视角静态链接自检（-static + --start-group） |

## 注意事项

- dietlibc 是 libc 本体，消费方式特殊：需 `-nostdlib -static -no-pie` + `start.o` + `dietlibc.a`，且 `main` 为三参数入口。
- 静态链接用 compiler-rt builtins（`clang -print-libgcc-file-name`）替代上游 `-lgcc`，并用 `--start-group` 解决 dietlibc↔builtins↔libpthread 循环依赖。
- 关键适配点：clang 集成汇编器（去 -fno-integrated-as + #function→%function + stlxr 寄存器）、llvm-ar 完整路径、libpthread wildcard、禁用 WANT_TLS/WANT_SSP（原生 TLS 与 clang emutls 冲突）、-static（避免 OHOS clang 默认 .interp 动态链接冲突）。
- 版本号 0.34-cvs20160606 为 Debian `0.34~cvs20160606` 的 Conan 化写法（`~` 改 `-`）。
---
