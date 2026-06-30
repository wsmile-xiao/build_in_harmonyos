# DateTime 1.66 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built (XS 编译成功，SELinux 限制阻塞运行)

## 编译步骤

1. 清理旧的 failed 状态归档
2. 初始化编译：`ohc-run.py init-build DateTime 1.66 --url=https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/DateTime-1.66.tar.gz`
3. 生成 Makefile，设置 CCFLAGS 包含 musl 头文件路径：
   ```bash
   export CCFLAGS="-I~/usr/local/include -D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64"
   perl Makefile.PL INSTALL_BASE=~/usr/local CCFLAGS="$CCFLAGS"
   ```
4. 编译 XS 代码：`make`（编译成功）
5. 手动链接（添加 -nostartfiles -nodefaultlibs -lc 参数）：
   ```bash
   clang -nostartfiles -nodefaultlibs -lc -shared -O2 -fstack-protector-strong DateTime.o -o blib/arch/auto/DateTime/DateTime.so
   ```
6. ELF 签名：`ohc-run.py sign-elf DateTime.so`
7. 安装到本地 Perl 模块目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 bits/alltypes.h 头文件 | musl 未编译，系统缺少 C 库头文件 | 编译 musl 1.2.5 获取完整头文件（已在 ~/usr/local/include） |
| 2 | unknown type name 'off64_t' | Perl 预编译包基于 glibc 构建，使用 glibc 特有的 off64_t 类型 | 在 ~/usr/local/include/bits/alltypes.h 添加 `typedef _Int64 off64_t;` |
| 3 | 链接失败：crti.o/crtbeginS.o 缺失 | musl 不提供 CRT 启动文件，glibc 环境不完整 | 使用 `-nostartfiles -nodefaultlibs -lc` 链接参数绕过 CRT 文件 |
| 4 | 纯 Perl 依赖缺失 | DateTime::Locale、DateTime::TimeZone 等未安装 | 已下载但依赖链不完整（B::Hooks::EndOfScope 等 XS 模块缺失） |
| 5 | **XS 模块无法加载** | SELinux HMDFS 限制：动态库必须有 `hnp_file:s0` 标签 | 需要管理员安装到 `/data/service/hnp` 系统目录 |

## 源码修改

- **~/usr/local/include/bits/alltypes.h**: 添加 `off64_t` typedef（glibc 兼容性）

## 依赖版本

### 已存在（必需）
- musl 1.2.5: ~/usr/local/include/bits/alltypes.h, ~/usr/local/lib/libc.a

### 已下载（纯 Perl）
- DateTime::Locale 1.45 (已复制到 site_perl)
- DateTime::TimeZone 2.68 (已复制到 site_perl)
- namespace::autoclean 0.31 (已复制，但缺 B::Hooks::EndOfScope)

### 缺失（阻塞）
- **B::Hooks::EndOfScope**: XS 模块，需编译
- Specio 系列
- Class::Method::Modifiers

## 功能测试结果

### XS 模块测试
```bash
$ file DateTime.so
ELF shared object, 64-bit LSB arm64, not stripped

$ perl -e 'use XSLoader; XSLoader::load("DateTime", "1.66");'
Can't load DateTime.so: Permission denied (SELinux HMDFS 限制)
```

### SELinux 限制分析
```
$ getfattr -d ~/usr/local/lib/.../DateTime.so | grep selinux
security.selinux="u:object_r:hmdfs:s0"  ← HMDFS 标签，不可加载

$ mount | grep currentUser
/data/service/el2/100/hmdfs/account on /storage/Users/currentUser type hmdfs
```

**结论**: DateTime.so 编译成功，但 HMDFS SELinux 限制导致无法动态加载。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| DateTime.so | 21KB | XS 共享库（已 ELF 砾名，SELinux 标签 hmdfs:s0） |
| DateTime.pm | ~30KB | Perl 模块主文件 |
| DateTime/*.pm | 多个 | 辅助模块 |
| functional-test-report.md | - | 功能测试报告 |

## 注意事项

1. **off64_t 兼容性**: musl 不提供 off64_t 类型，需要在 alltypes.h 中手动添加 typedef
2. **链接参数**: Perl XS 模块链接必须使用 `-nostartfiles -nodefaultlibs -lc` 参数
3. **SELinux HMDFS 限制**: 用户目录（HMDFS）上的动态库无法加载，必须安装到 `/data/service/hnp` 系统目录
4. **依赖链**: B::Hooks::EndOfScope 等 XS 依赖缺失，需逐个编译

## 安装指南（管理员操作）

DateTime.so 需要管理员安装到系统目录才能获得正确的 SELinux 标签：

```bash
# 1. 创建 HNP 包（包含 DateTime.so）
# 2. 管理员安装
sudo -u installs unzip ~/tmp/DateTime.hnp -d /data/service/hnp/perl.org/perl_5.42.0/

# 3. 重新签名（获得正确 SELinux type）
/data/service/hnp/bin/binary-sign-tool sign -inFile ... -outFile ... -selfSign 1

# 4. 验证
perl -MDateTime -e 'print "DateTime OK\n";'
```

## 知识沉淀

- **E112 扩展**: musl 缺少 off64_t 类型定义，需要在 alltypes.h 中添加 `typedef _Int64 off64_t;`
- **Perl XS 模块链接**: 使用 `-nostartfiles -nodefaultlibs -lc` 绕过 CRT 文件缺失问题
- **glibc/musl 兼容性**: Perl 预编译包基于 glibc，其 XS 模块依赖 glibc 特有类型（off64_t）
- **E046 SELinux HMDFS**: 用户目录上的动态库无法加载，必须安装到系统目录（参考 perl-dbd-pg）

---

**编译结束**: 2026-06-10
**最终状态**: built (XS 编译成功，运行受限 - 需管理员干预)
---

**编译结束**: 2026-06-10 15:32
**最终状态**: built
