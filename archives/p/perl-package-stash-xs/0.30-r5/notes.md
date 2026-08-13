# perl-package-stash-xs 0.30-r5 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-02
- 编译器: clang 18.1.8
- Perl: v5.42.0 (aarch64-linux)
- 状态: built

## 编译步骤

1. 下载源码: https://cpan.metacpan.org/authors/id/E/ET/ETHER/Package-Stash-XS-0.30.tar.gz
2. 修改 Makefile.PL 添加 HarmonyOS 适配参数 (见源码修改节)
3. perl Makefile.PL PREFIX=$DEFAULT_PREFIX
4. make (编译 XS.c → XS.o → XS.so)
5. make install DESTDIR=$TEST_PREFIX
6. make test (测试因平台限制失败，见下文)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sys/types.h` not found | 鸿蒙系统缺少标准C头文件 | Makefile.PL 添加 INC 指向 `_sysheaders_backup` 和 `usr/local/include` |
| 2 | `endian.h` not found | sys/types.h 引用 endian.h 但不在默认搜索路径 | 同上，添加 `-I/storage/Users/currentUser/usr/local/include` |
| 3 | `unable to find library -lc` | 鸿蒙 libc.so 在 /system/lib64 非标准路径 | OTHERLDFLAGS 添加 `-L/system/lib64` |
| 4 | CRT 文件缺失 (crti.o 等) | 鸿蒙系统无 CRT 启动文件 | OTHERLDFLAGS 添加 `-nostartfiles -nodefaultlibs` |
| 5 | make test: Permission denied 加载 .so | SELinux HMDFS 限制，用户目录 .so 无法动态加载 | 平台限制，记录不阻塞。编译和链接本身成功 |

## 源码修改

### Makefile.PL 修改

在 `WriteMakefile(%WriteMakefileArgs)` 调用前添加以下内容:

```perl
# HarmonyOS: missing CRT files (crti.o, crtn.o, crtbeginS.o, crtendS.o)
# Add link flags to bypass startup files
$WriteMakefileArgs{dynamic_lib} = { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -L/system/lib64 -lc' };
# HarmonyOS: system headers are in backup directory
$WriteMakefileArgs{INC} = '-I/storage/Users/currentUser/usr/local/include/_sysheaders_backup -I/storage/Users/currentUser/usr/local/include';
```

## 依赖版本

- Perl: v5.42.0 (aarch64-linux)
- Package::Stash: 已安装 (perl-package-stash 依赖已满足)
- XSLoader: 0.32 (Perl 内置)
- clang: 18.1.8
- make: GNU Make 4.4.1

## 验证结果

```
# 编译成功
clang -c -I.../_sysheaders_backup -I.../usr/local/include ... XS.c  → XS.o (1 warning, non-fatal)
clang -shared XS.o -nostartfiles -nodefaultlibs -L/system/lib64 -lc -o XS.so  → 成功

# 产物验证
file XS.so: ELF shared object, 64-bit LSB arm64, not stripped
readelf -d XS.so: NEEDED libc.so, BIND_NOW, FLAGS_1 NOW

# make test 结果
t/00-report-prereqs.t .... ok  (通过)
t/zzz-check-breaks.t ..... ok  (通过)
其余 16 个测试文件因 SELinux HMDFS 限制无法加载 .so 而失败 (Permission denied)
这是平台限制，非编译问题
```

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| XS.so | blib/arch/auto/Package/Stash/XS/XS.so | Perl XS 共享库 (ELF aarch64) |
| XS.pm | blib/lib/Package/Stash/XS.pm | Perl 模块文件 |

## 注意事项

- 鸿蒙系统缺少标准 C 头文件 (sys/types.h, endian.h 等)，需要通过 INC 指向 `_sysheaders_backup` 目录
- 鸿蒙 libc.so 位于 /system/lib64，非标准路径，链接时需要 `-L/system/lib64`
- 鸿蒙系统无 CRT 启动文件 (crti.o, crtn.o, crtbeginS.o, crtendS.o)，XS 模块链接需要 `-nostartfiles -nodefaultlibs`
- SELinux HMDFS 限制导致用户目录下的 .so 无法被 dlopen 加载，make test 大部分测试因此失败
- 这是 XS 模块在鸿蒙平台的通用限制，非本模块特有问题

## 功能测试结果 (2026-07-02)

### 编译产物验证
- XS.so: ELF64 AArch64 共享对象，34,240 bytes，仅依赖 libc.so ✅
- 安全特性: NX (GNU_STACK RW) + RELRO (GNU_RELRO) + BIND_NOW ✅
- ELF 签名: .codesign section 存在 ✅
- 导出符号: boot_Package__Stash__XS (Perl XS bootstrap) ✅
- 源码 SHA256: 26bad65c... 与 conandata.yml 一致 ✅

### 模块加载测试
- 系统模块 (strict, Cwd, File::Spec): ✅ 全部通过
- Package::Stash (纯 Perl v0.40): ✅ 加载成功
- Package::Stash::XS: ❌ SELinux HMDFS 限制 (Permission denied)
  - 用户目录 .so 上下文: u:object_r:hmdfs:s0 → 不可加载
  - 系统目录 .so 上下文: u:object_r:hnp_file:s0 → 可加载 (参照 Cwd.so)

### Package::Stash 功能测试 (PP 后端)
- add_symbol (scalar/array/hash/code): ✅ 全部通过
- get_symbol: ✅ 正确返回所有类型
- list_all_symbols: ✅ 返回正确符号列表
- has_symbol: ✅ 存在/不存在检测正确
- remove_symbol: ✅ 删除后符号消失

### HNP 安装包
- 包名: perl-package-stash-xs, 版本: 0.30-r5
- 文件: perl-package-stash-xs.hnp (19,242 bytes)
- 包含: XS.so (已签名), XS.pm, Stash.pm
- 安装目标: /data/service/hnp/perl.org/perl_5.42.0/
- 状态: HNP 包已创建，需 installs 用户安装

### Conan 配方验证
- conan-verify: ✅ 全部门禁通过 (G0-G4 + L2/L4/L5)
- conan create: ✅ 从源码构建成功

## 上库评估
- 满足所有上库要求 (conanfile.py, conandata.yml, test_package/, patches/, conan-verify)
- 建议状态: built (verify 通过，未 CI upload)

## 参考: perl-dbd-pg 编译经验
- 相同的 CRT 文件缺失问题 → -nostartfiles -nodefaultlibs -lc
- 相同的 SELinux HMDFS 限制 → 需安装到 /data/service/hnp 系统目录
- 相同的 Makefile.PL dynamic_lib OTHERLDFLAGS 适配方法
- perl-dbd-pg 已验证 HNP 包安装方案的可行性

---

**编译结束**: 2026-07-02 15:25
**测试完成**: 2026-07-02 20:10
**最终状态**: built (编译成功，待 HNP 安装)
