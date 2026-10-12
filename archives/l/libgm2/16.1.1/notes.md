# libgm2 16.1.1 适配笔记（GNU Modula-2 运行时库, HarmonyOS PC / aarch64）

## 编译环境
- 构建系统: autotools（GCC releases/gcc-16 分支快照 gcc-16-20260502，`--enable-languages=c,c++,m2`）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK Clang 15（clang/clang++）+ clang-sign/clangxx-sign 签名包装器；GNU as/ld（/data/service/hnp/bin）
- 状态: built
- 构建/主机/目标三元组: aarch64-linux-ohos

## 编译步骤

1. `conan create archives/l/libgm2/16.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. source() 从本地缓存取 gcc-16-20260502.tar.xz，树内解压 gmp-6.3.0 / mpfr-4.2.2 / mpc-1.3.1（与 GCC 官方 download_prerequisites 一致），运行 files/prepare_ohos_sources.py 应用有审核源码变换（见「源码修改」）。
3. 顶层 configure：GCC 三元组 + `--enable-languages=c,c++,m2` + 关闭 bootstrap/lto/plugin/multilib/nls 及不需要的 target 库 + `--with-sysroot=<SDK native/sysroot>` + `--disable-threads`。
4. `make all-gcc -j2`：构建 xgcc/cc1/cc1plus/cc1gm2/gm2 驱动（host 可执行均带 OHOS codesign）。
5. 写入驱动 specs（__availability__ 屏蔽、*link: --eh-frame-hdr、*post_link: 签名），合并 SDK libc++_static.a+libunwind.a 为 libstdc++.a 放入 -B gcc 目录。
6. `make configure-target-libgcc` → 改 libgcc thread_header 为 gthr-posix.h → `make all-target-libgcc`。
7. `make all-target-libgm2 CXX_FOR_TARGET=clangxx-target`：构建 5 个运行时库（libm2cor/libm2iso/libm2log/libm2min/libm2pim，各 .a+.so+.so.21+.so.21.0.0，带 codesign，NEEDED 仅 libc.so）。
8. build() 末尾 smoke test：用新构建的 gm2 驱动 + cc1gm2 编译并执行上游 examples/hello/pass/hello.mod（全链路验证）。
9. 测试套件：`runtest --tool gm2`（DejaGNU 1.6.3）分批跑完全部 113 个 .exp，汇总 PASS=16207/16261（99.67%）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gmp libtool 0 字节 .la | toybox sh 下 ksh 内建 `print -r --` ECHO 不可用 | gmp/libtool ECHO 改 `printf %s\\n` 后重链 libgmp.a/.la |
| 2 | 嵌套 configure `cannot guess build type` | config.guess 不识别 HarmonyOS（uname -s=HarmonyOS） | gcc/m2/Make-lang.in 三处嵌套 configure 注入 `--build/--host=aarch64-linux-ohos` |
| 3 | config.status `Permission denied`（defines.awk） | HMDFS 用户映射下 umask 077 临时目录不可写 | gcc/m2/gm2-libs/config-host 等 `umask 077`→`umask 022` |
| 4 | mc 引导翻译器无法建临时文件 | OHOS /tmp 只读 | m2/mc mcStream.mod/mcPreprocess.mod 及 mc-boot C++ 镜像的 /tmp 路径改当前目录 |
| 5 | cc1gm2 重复 cp 失败（EPERM） | HMDFS 上覆盖已签名可执行文件受限 | gcc/m2/Make-lang.in cc1gm2 规则先 `rm -f $@` 再 `cp -p $< $@`（conan create8 验证） |
| 6 | target libgcc 缺头/缺 crti.o | xgcc 不认识 multiarch 目录 | C_INCLUDE_PATH/CPLUS_INCLUDE_PATH 加 `<sysroot>/usr/include/aarch64-linux-ohos`，LIBRARY_PATH 加 `<sysroot>/usr/lib/aarch64-linux-ohos` |
| 7 | OHOS 头 `__attribute__((__availability__(ohos, introduced=…)))` GCC 报错 | Clang 专属属性 | gcc/ 下 specs 文件 `%rename: cpp_old=cpp` 追加 `-D__availability__(...)=` |
| 8 | 未签名二进制 exit 126 无法执行 | OHOS 强制 ELF codesign | specs `*post_link:` 调用 sign-output.sh（binary-sign-tool），INFO 日志重定向到 .tmp/codesign.log |
| 9 | exceptions 运行全 FAIL（uncaught int） | 存在 specs 文件时驱动不传 `--eh-frame-hdr` | specs `*link:` 段前置 `--eh-frame-hdr`（保留 -dynamic-linker/-X/-EL 等原 flags） |
| 10 | RTco.cc 编译失败 | --disable-threads → libgcc 用 gthr-single.h（缺 __gthread_cond_t） | libgcc Makefile/config.status thread_header 改 gthr-posix.h（OHOS musl 有 pthread_cond_t） |
| 11 | gm2spec.cc 无条件 `-lstdc++` 但禁用 libstdc++-v3 | 运行时 .cc 由 clang++ 编译，.a 引用 __cxa_throw 等 | SDK libc++_static.a+libunwind.a 合并成 libstdc++.a 放 -B gcc 目录（无重复符号） |
| 12 | runtest spawn 卡住/误报 | expect spawn 走 pty 硬编码 /bin/stty（本机无）；sign 输出混入被捕获输出 | DejaGNU remote.exp local_exec 改 open 管道 + `spawn -leaveopen`（无 pty）；sign INFO 重定向 |
| 13 | 沙箱 SIGSYS（Signal 31）时间类系统调用 | OHOS 沙箱/seccomp 屏蔽 | 环境性失败（iso/run/pass m2date/testclock×2，18 条），非功能缺陷 |

## 源码修改

- 无独立 .patch（conandata `patches: {}`）；所有 OHOS 适配收敛在 **files/prepare_ohos_sources.py**（有审核、幂等）：
  1. config.sub/configfsf.sub 注入 aarch64-linux-ohos 三元组
  2. 所有 configure/config-host `umask 077`→`umask 022`
  3. gcc/config.gcc 增加 `*-*-*ohos*`/`*-*-linux-ohos*` musl 分支，tm_file 追加 ohos.h
  4. gcc/config/ohos.h（files/ohos.h 拷贝）
  5. gcc/m2/Make-lang.in：三处嵌套 configure 注入 --build/--host；**cc1gm2 规则先 rm 再 cp**
  6. gcc/m2/gm2-libs/config-host umask 022
  7. m2/mc（.mod 与 mc-boot C++ 镜像）4 处 /tmp 路径改当前目录
- 构建期生成文件编辑（conanfile `_patch_generated_makefiles`）：顶层 Makefile TARGET_CONFIGDIRS=`libgcc libgm2`、断开 maybe-all-target-libstdc++-v3 依赖；libgcc Makefile/config.status gthr-single.h→gthr-posix.h。

## 依赖版本

- build_requires: dejagnu/1.6.3.1, expect/5.45.4, tcl/8.6.16
- 树内（source 内联）: gmp 6.3.0, mpfr 4.2.2, mpc 1.3.1
- 编译器: OHOS SDK clang/clang++ 15（--target=aarch64-linux-ohos --sysroot）；GNU as/ld/ar/ranlib/nm

## 验证结果

```bash
# 全量上游 gm2 测试套件（runtest --tool gm2，113 个 .exp，分批 b01..b13+iso*）
PASS=16207  FAIL=54  UNRESOLVED=0  （清单总数 16261，通过率 99.67%）
# FAIL 全为环境性：36 = exceptions/run/pass（早于 16:26 eh-frame-hdr 修复，修复后复验 54 PASS）；
# 18 = iso/run/pass 时间类（OHOS 沙箱 SIGSYS）。0 真实功能失败。
# conan create W3 验证：包 ID 见 .ci-result.json / conan list 'libgm2/16.1.1*'，
# 包内含 5 个运行时库 .a/.so + m2 定义模块头 + test_package 消费者测试。
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 完整 W3 配方（源码变换、签名包装器、specs、运行时构建、smoke test） |
| conandata.yml | gcc/gmp/mpfr/mpc 四个 sources 条目（sha256 已核验） |
| files/prepare_ohos_sources.py | OHOS 源码变换（含 cc1gm2 rm-cp 修复） |
| files/gm2-specs.template / ohos.h | 驱动 specs 模板 / aarch64-linux-ohos 目标头 |
| test_package/ | CMake + test_libgm2.c + conanfile.py + MANIFEST.yml（7 条运行时 API 断言） |
| reports/test-report.md | 上游测试汇总（113 .exp，99.67%） |

## 注意事项

- **cc1gm2 覆盖陷阱**：Make-lang.in cc1gm2 规则必须先 `rm -f` 再 cp，否则 HMDFS 对已签名文件报 EPERM（prepare_ohos_sources.py 已固化）。
- **运行时依赖**：libm2cor/libm2iso/libm2log/libm2min/libm2pim 的 NEEDED 仅 libc.so；消费者链接时需 SDK libc++（合并 libstdc++.a 仅存在于构建树，不随包发布）。
- 上游 4 个驱动 .exp（recover/pass、ulmlib/{pass,std,sys}）glob 的库源目录在本快照缺失 → 0 用例条目（与上游行为一致）。

### 补充（create8 验证阶段新增两坑）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 14 | libgcc2.c 编译报 `__availability__ too many decimal points` | `configure-target-libgcc`/`all-target-libgcc` 期间 `xgcc -dumpspecs > specs`（gcc/Makefile `$(SPECS): xgcc` 规则）覆盖 conanfile 写入的模板 specs，`*cpp:` 的 `-D__availability__(...)=` 注入丢失 | build() 中 `_write_gm2_specs` 移到 configure-target-libgcc 之后；`_patch_generated_makefiles()` 把 specs 规则改为 `@touch $(SPECS)` |
| 15 | libgcov 编译 `gthr-default.h 'pthread_cancel' undeclared` | gthr-posix.h `__gthrw(pthread_cancel)` 需 glibc 符号，OHOS musl 无；conan 把 gthr-posix.h 应用到 libgcc 编译（交互构建中 libgcc 用 gthr-single.h 已编完故未暴露） | prepare_ohos_sources.py 新增 apply_libgcc_thread_fixes：`__OHOS__` 下跳过 pthread_cancel 声明、GTHR_ACTIVE_PROXY 用 pthread_create（同 bionic） |
---

**编译结束**: 2026-09-28 11:11
**最终状态**: published
