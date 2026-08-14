# perl-par-packer 1.064-r2 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03 (修订)
- 编译器: clang 18.1.8
- 状态: built → published (parl 生成已修复)

## 编译步骤

1. 安装缺失的 Perl 依赖模块: PAR, Archive::Zip, Getopt::ArgvFile, ExtUtils::Depends (via cpan -T)
2. 修改所有 Makefile PL 文件添加 OHOS 适配参数
3. `perl Makefile.PL` 生成 Makefile
4. `make -j1 -k` 编译（-k 继续跳过 parl 构建失败）
5. **关键修复**: 使用 `PAR_GLOBAL_TEMP` 环境变量生成 parl/parldyn
6. 手动安装 blib 文件到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-fstack-protector-strong` 链接错误 | Perl Config 的 ldflags/lddlflags 包含此编译器标志，但 ld.lld 不识别 | 在 WriteMakefile 中覆盖 CCFLAGS/LDFLAGS/LDDLFLAGS，移除该标志 |
| 2 | `sys/types.h` not found | OHOS 系统无标准 C 库头文件 | 使用 `--sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot` 指向 OHOS SDK sysroot |
| 3 | `off64_t` 未定义 | OHOS musl libc 不提供 glibc 的 off64_t 类型 | 添加 `-Doff64_t=off_t` 到 CCFLAGS |
| 4 | CRT 文件缺失 (crti.o, crtn.o, crt1.o) | OHOS 默认链接路径不含 CRT 文件 | 使用 `-nostartfiles -nodefaultlibs` + 显式指定 sysroot 中的 CRT 文件路径 |
| 5 | `libunwind.a` not found | clang 默认链接 libunwind，但 sysroot 中不存在 | `-nodefaultlibs` 跳过默认库，显式添加 `-lc` |
| 6 | soft-float 符号未定义 (__extenddftf2, __addtf3 等) | `-nodefaultlibs` 移除了 compiler-rt builtins | 显式添加 `libclang_rt.builtins.a` 到链接参数 |
| 7 | `ldd` 命令不存在 | OHOS 系统无 ldd 工具 | 创建 ldd wrapper 脚本使用 readelf -d 替代 |
| 8 | ExtUtils::CBuilder 编译器检测失败 | 上述多个问题导致测试编译链接失败 | 强制 `$have_cc = 1` 绕过检测 |
| 9 | **parl 二进制无法生成** (已修复) | boot/par 执行时 `par_mktmpdir()` 的 `isSafeDir()` 在 HMDFS 上失败（权限 0700 检查不通过） | **使用 `PAR_GLOBAL_TEMP` 环境变量**: `par_init_env()` 将其复制为 `PAR_TEMP`，跳过所有临时目录创建和安全检查 |
| 10 | XS 模块 .so 链接需要特殊参数 | 鸿蒙缺少 CRT 文件，标准链接流程失败 | 添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }` 和 `LDDLFLAGS` 覆盖 |

## 关键修复: PAR_GLOBAL_TEMP 绕过 HMDFS 安全检查

### 问题
`par_mktmpdir()` (mktmpdir.c) 创建临时目录 `$TMPDIR/par-$USER/` 后调用 `isSafeDir()` 检查:
1. 目录必须是真实目录 (S_ISDIR)
2. 目录必须由当前用户拥有 (st_uid == getuid())
3. 目录权限必须为 0700

HMDFS 不支持 Unix 权限模型，`mkdir(dir, 0700)` 创建的目录权限不为 0700，安全检查失败。

### 解决方案
`par_init_env()` (utils.c) 检查 `PAR_GLOBAL_TEMP` 环境变量:
```c
if ( (buf = par_getenv("PAR_GLOBAL_TEMP")) != NULL ) {
    par_setenv("PAR_TEMP", buf);
}
```
`par_mktmpdir()` 首先检查 `PAR_TEMP`，若已设置则直接返回，跳过所有目录创建和安全检查。

### 使用方法
```bash
# 生成 parl
PAR_GLOBAL_TEMP=$TMPDIR/par_global_temp \
  perl -Mblib=.. run_with_inc.pl ./boot -q -B -Oparl

# 生成 parldyn
PAR_GLOBAL_TEMP=$TMPDIR/par_global_temp_dyn \
  perl -Mblib=.. run_with_inc.pl ./par -q -B -Oparldyn
```

## 签名修复: parl/parldyn 签名失效解决 (已修复)

### 问题
parl = boot + 追加的 PAR 数据。追加数据后 `.codesign` 签名失效，OHOS 内核拒绝执行 (EPERM)。

### 根因分析
- `binary-sign-tool` 之前失败是因为缺少必填参数 `-keyAlias` 和 `-signAlg`
- 签名工具只处理 ELF 结构内的数据，忽略 ELF 后追加的裸数据
- 直接签名会丢弃追加的 PAR 数据

### 解决方案: ELF section 嵌入 + 重新签名

```bash
# 1. 从 parl 提取追加的 PAR 数据 (boot 之后的所有字节)
tail -c +$((BOOT_SIZE + 1)) parl > par_data.bin

# 2. 从 boot 移除旧的 .codesign section
objcopy --remove-section=.codesign boot boot_nosig

# 3. 将 PAR 数据添加为 .pardata ELF section
objcopy --add-section .pardata=par_data.bin \
  --set-section-flags .pardata=alloc,load,contents,data \
  boot_nosig parl_with_section

# 4. 用 binary-sign-tool 签名 (关键: 需要 -keyAlias 和 -signAlg)
binary-sign-tool sign \
  -keyAlias "parl-key" \
  -signAlg SHA256withECDSA \
  -selfSign 1 \
  -inFile parl_with_section \
  -outFile parl_signed
```

### 验证结果
- ✅ `binary-sign-tool display-sign` 确认签名有效 ("code signature is self-sign")
- ✅ 签名后的 parl 可以执行 (不再报 "Operation not permitted")
- ✅ `find_par_magic()` 在 `.pardata` section 中找到 PAR magic (扫描整个文件)
- ⚠️ XS .so 模块加载仍受 HMDFS SELinux 限制 (同 perl-dbd-pg，需安装到系统目录)

### ELF 结构
```
.pardata  PROGBITS  0x5e9577  15ce8e  WA  (PAR 数据, 1.4MB)
.codesign PROGBITS  0x74a000  001000      (签名, 4KB)
```

## 平台限制 (部分已修复)

| 限制 | 根因 | 状态 | 影响 |
|------|------|------|------|
| ~~parl/parldyn 无法执行~~ | ~~签名失效~~ | ✅ 已修复 | ELF section 嵌入 + 重新签名 |
| PAR 模块运行时临时目录 | PAR::SetupTemp HMDFS 安全检查 | ❌ 平台限制 | `perl -MPAR` 需 PAR_GLOBAL_TEMP |
| XS .so 运行时加载 | SELinux HMDFS 限制 | ❌ 平台限制 | 需安装到 /data/service/hnp |
| pp -o 创建可执行文件 | pp 提取的临时 parl 无签名 | ⚠️ 需后处理 | 可用 pp -p + 手动签名替代 |

### 替代方案
- 使用 `pp -p` 创建 .par 文件 (替代 pp -o 创建可执行文件)
- 使用 `par.pl` 运行 .par 文件 (替代 parl 独立执行)

## 源码修改

### Makefile.PL (主)
- 强制 `$have_cc = 1` 绕过 CBuilder 检测
- 添加 `CCFLAGS` 覆盖（含 `--sysroot`, `-Doff64_t=off_t`，移除 `-fstack-protector-strong`）
- 添加 `LDFLAGS` 和 `LDDLFLAGS` 覆盖（含 `--sysroot`, `-nostartfiles -nodefaultlibs -lc`）
- 在 WriteMakefile1 中添加 `$params{dynamic_lib} = { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }`

### myldr/Makefile.PL
- 添加 `--sysroot` 到 $cc 和 $ld
- 从 $pccflags/$pldflags 中移除 `-fstack-protector-strong`
- 添加 `-Doff64_t=off_t` 到 $cflags
- 修改 $ldflags: 添加 CRT 文件路径、`-nostartfiles -nodefaultlibs`、`libclang_rt.builtins.a`、`-lc`
- 创建 ldd wrapper 脚本替代缺失的 ldd 命令

### t/data/XSFoo/Makefile.PL, t/data/XSQuux/Makefile.PL, t/data/XSBar/Makefile.PL
- 添加 `CCFLAGS`, `LDFLAGS`, `LDDLFLAGS`, `dynamic_lib` 参数（同主 Makefile.PL）

## 依赖版本

- Perl 5.42.0 (静态链接, libperl.a)
- PAR 1.021
- PAR::Dist 0.53
- Archive::Zip 1.68
- Getopt::ArgvFile 1.11
- ExtUtils::Depends 0.8002
- Module::ScanDeps 1.37
- OHOS SDK 26.0.0.18 (sysroot)
- clang 18.1.8

## 验证结果

### 编译验证
```
# XSFoo.so 编译链接成功 (9472 bytes)
clang --sysroot=... -shared -nostartfiles -nodefaultlibs -lc XSFoo.o -o XSFoo.so

# par 可执行文件链接成功 (4MB)
clang --sysroot=... main.o sha1.o -nostartfiles -nodefaultlibs crti.o crt1.o crtn.o -lperl libclang_rt.builtins.a -lc -o par

# boot 可执行文件链接成功 (6.2MB)
clang --sysroot=... boot.o sha1.o -nostartfiles -nodefaultlibs crti.o crt1.o crtn.o -lc -o boot

# parl 生成成功 (7.6MB) - 使用 PAR_GLOBAL_TEMP 修复
PAR_GLOBAL_TEMP=... perl -Mblib=.. run_with_inc.pl ./boot -q -B -Oparl

# parldyn 生成成功 (5.4MB) - 使用 PAR_GLOBAL_TEMP 修复
PAR_GLOBAL_TEMP=... perl -Mblib=.. run_with_inc.pl ./par -q -B -Oparldyn
```

### 功能验证
```
# Perl 模块加载 ✅
perl -MPAR::Packer -e 'print $PAR::Packer::VERSION'  → 1.064

# pp 工具 ✅
pp -V  →  PAR Packager, version 1.064 (PAR version 1.021)

# .par 文件创建 ✅
pp -p -o hello.par hello.pl  →  hello.par (1427 bytes)

# .par 文件运行 ✅
par.pl hello.par  →  Hello from PAR::Packer!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| myldr/par | ~4MB | PAR 打包器可执行文件 (动态, 已签名) |
| myldr/boot | ~6.2MB | PAR 引导加载器 (静态, 已签名) |
| myldr/parl | ~7.6MB | 完整 PAR 打包器 (静态, 已签名) |
| myldr/parldyn | ~5.4MB | 完整 PAR 打包器 (动态, 已签名) |
| blib/arch/auto/XSFoo/XSFoo.so | 9472 | XS 模块共享库 |
| blib/lib/PAR/Packer.pm | 50KB | 主模块 |
| blib/lib/PAR/StrippedPARL/Static.pm | ~8.6MB | 静态 PARL 数据 (内嵌 boot) |
| blib/lib/PAR/StrippedPARL/Dynamic.pm | ~5.5MB | 动态 PARL 数据 (内嵌 par) |
| blib/lib/pp.pm | - | pp 打包工具模块 |
| blib/script/par.pl, pp, tkpp, parl, parldyn | - | 脚本文件 |

## 注意事项

- parl/parldyn 已通过 ELF section 嵌入 + binary-sign-tool 重新签名，可在 OHOS 上执行
- 推荐使用 .par 文件 + par.pl 方案替代独立可执行文件
- 所有 XS 模块的 Makefile.PL 都需要添加 OHOS 适配参数
- `PAR_GLOBAL_TEMP` 是绕过 HMDFS 安全检查的关键环境变量
- 生成 parl/parldyn 时必须设置 `PAR_GLOBAL_TEMP`，否则会因 HMDFS 安全检查失败

## 与 perl-dbd-pg 编译经验对照

| 方面 | perl-dbd-pg | perl-par-packer |
|------|-------------|-----------------|
| 构建系统 | Makefile.PL | Makefile.PL |
| CRT 文件缺失 | -nostartfiles -nodefaultlibs -lc | ✅ 相同方案 |
| -fstack-protector-strong | - | ✅ 从 ldflags 中移除 |
| off64_t 未定义 | - | ✅ -Doff64_t=off_t |
| sysroot 指定 | --sysroot | ✅ 相同方案 |
| ldd 命令缺失 | - | ✅ readelf wrapper |
| HMDFS 临时目录限制 | SELinux 限制 .so 加载 | ✅ PAR_GLOBAL_TEMP 绕过 |
| 签名问题 | .so 需签名 | ✅ ELF section 嵌入 + 重新签名 |
| HNP 安装包 | ✅ 已准备 | 可准备（需管理员安装） |

---

**编译结束**: 2026-07-03 15:40
**最终状态**: published (编译成功，parl 生成已修复，conan-verify 通过)
