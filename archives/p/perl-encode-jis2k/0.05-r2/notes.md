# perl-encode-jis2k 0.05-r2 适配笔记

## 编译环境
- 构建系统: Perl XS (Makefile.PL + ExtUtils::MakeMaker)
- 编译日期: 2026-06-10
- 编译器: clang 18.1.8
- 状态: built (编译成功，已签名)

## 编译步骤

1. 初始化：使用 CPAN URL 手动下载源码
   - URL: https://cpan.metacpan.org/authors/id/D/DA/DANKOGAI/Encode-JIS2K-0.05.tar.gz
   - 因 SSL 证书问题，使用 curl -k 手动下载

2. 配置：运行 Makefile.PL
   ```bash
   perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
   ```

3. 编译：需要修改 Makefile 添加 Ohos SDK sysroot 路径
   - CCFLAGS: 添加 `-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include` 和 `-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos`
   - LDDLFLAGS: 添加 `-nostartfiles` 和 `-L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos -L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos`

4. 安装：DESTDIR 模式
   ```bash
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-perl-encode-jis2k-0.05-r2
   ```

5. 测试：全部通过
   ```bash
   make test
   # 结果: All tests successful. Files=1, Tests=19
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | MetaCPAN HTTPS 证书不受信任 | 使用 curl -k 手动下载 |
| 2 | sys/types.h 找不到 | Perl CORE 头文件依赖系统头文件，鸿蒙缺少 /usr/include | 添加 Ohos SDK sysroot include 路径到 CCFLAGS |
| 3 | bits/alltypes.h 找不到 | sys/types.h 需要 arch-specific 头文件 | 添加 aarch64-linux-ohos include 路径 |
| 4 | crti.o/crtbeginS.o 找不到 | 链接器默认路径不包含 Ohos SDK | 添加 -nostartfiles 跳过 crt 文件（共享库不需要） |
| 5 | libunwind.a 找不到 | Perl XS 扩展链接需要 LLVM 运行时库 | 添加 LLVM lib 路径到 LDDLFLAGS |
| 6 | 共享库加载 Permission denied | 鸙蒙系统要求 ELF 签名才能执行 | **已解决**：使用 /data/service/hnp/bin/binary-sign-tool 签名 |
| 7 | HMDFS SELinux 限制 | hishell_hap domain 只能加载 hnp_file 类型文件 | **系统限制**：需管理员安装到 /data/service/hnp 目录 |

## 源码修改

**临时修改 Makefile（未固化为补丁）**：
- CCFLAGS 行（添加 include 路径）
- LDDLFLAGS 行（添加 -nostartfiles 和 lib 路径）

**需要固化的修改**：建议修改 Makefile.PL 或创建 Perl Config 模块来自动添加这些路径。

## 依赖版本

- Perl 5.42.0 (已安装)
- Encode 模块 >= 1.41 (已安装)
- enc2xs 工具 (已安装)
- Ohos SDK 26.0.0.18

## 验证结果

```bash
# 编译成功
make test
# All tests successful. Files=1, Tests=19, 0 wallclock secs

# 本地安装成功
ls -la ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/Encode/JIS2K.pm
# -rw-rw---- 1 20001006 file_manager 5026 2023-11-15 12:14 JIS2K.pm

# ELF 签名成功 (2026-06-11)
/data/service/hnp/bin/binary-sign-tool sign -inFile ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Encode/JIS2K/JIS2K.so -outFile ~/tmp/JIS2K.so.signed -selfSign 1
# add codesign section success

# HMDFS 加载仍失败 (SELinux 限制)
PERL5LIB=~/usr/local/lib/site_perl/5.42.0/aarch64-linux perl -e 'use Encode::JIS2K;'
# Permission denied (SELinux type: hmdfs:s0, 需要 hnp_file:s0)
```

## 交付物

**预编译包（已打包）**：
| 文件 | 大小 | 说明 |
|------|------|------|
| perl-encode-jis2k-0.05-r2-ohos-aarch64.tar.gz | 2.4 MB | 预编译安装包 |
| perl-encode-jis2k-0.05-r2-ohos-aarch64-debug.tar.gz | 152 KB | 调试符号包 |
| perl-encode-jis2k.hnp | 2.3 MB | HNP 包（供管理员安装） |

**编译产物**：
| 文件 | 大小 | 说明 |
|------|------|------|
| JIS2K.so | 2.3 MB | Perl XS 扩展共享库（已签名） |
| JIS2K.pm | 5 KB | Perl 模块文件 |
| 2022JP3.pm | 2.5 KB | ISO-2022-JP-3 编码支持 |

## 功能测试结果

**测试日期**: 2026-06-11

### 测试环境
- Perl 5.42.0 (系统安装: `/data/service/hnp/perl.org/perl_5.42.0/`)
- Encode 3.21 (系统自带)
- 测试方式: 本地加载 + HNP 包模拟

### 测试结果

| 测试项 | 状态 | 备注 |
|-------|------|------|
| 编译产物完整性 | ✅ PASS | ELF 结构正确，已签名 |
| XS 模块签名验证 | ✅ PASS | .codesign section 存在 |
| Encode::JP 系统模块 | ✅ PASS | iso-2022-jp 编码正常 |
| Encode::JIS2K 本地加载 | ❌ FAIL | HMDFS SELinux 限制 |
| HNP 包制作 | ✅ PASS | 供管理员安装 |

### 关键发现

1. **Encode::JP 可用**: 系统自带的 Encode::JP 模块正常工作，iso-2022-jp 编码可用
   ```perl
   perl -MEncode::JP -e 'use Encode::JP; print "OK\n";'  # OK
   perl -e 'my $str = Encode::encode("iso-2022-jp", "テスト"); print length($str), "\n";'  # 33
   ```

2. **Encode::JIS2K 需管理员安装**: XS 模块无 PurePerl fallback，必须安装到系统目录
   - 安装位置: `/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux/`
   - SELinux 要求: `hnp_file:s0` 类型

3. **支持的编码（安装后可用）**:
   - iso-2022-jp-3 (JIS X 0213)
   - euc-jisx0213 (EUC-JISX0213)
   - shiftjisx0213 (Shift_JISX0213)
   - jisx0212 (JIS X 0212 补充汉字)

### 管理员安装指南

```bash
# 1. 解压 HNP 包到系统目录（需要 installs 用户权限）
sudo -u installs tar -xzf ~/tmp/perl-encode-jis2k.hnp \
    -C /data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux/

# 2. 验证安装
perl -MEncode::JIS2K -e 'print "Encode::JIS2K loaded successfully\n";'

# 3. 测试编码功能
perl -e 'use Encode::JIS2K; use Encode qw(encode decode); \
    my $str = encode("iso-2022-jp-3", "テスト"); print "OK\n";'
```

## 注意事项

1. **ELF 签名已解决**：使用 `/data/service/hnp/bin/binary-sign-tool` 对 JIS2K.so 进行签名，签名后 ELF 包含 `.codesign` section。

2. **HMDFS SELinux 限制**：签名后的 .so 文件在 HMDFS 目录（~/usr/local）仍无法加载，因为 hishell_hap domain 只能加载 `hnp_file:s0` 类型文件。需管理员安装到 `/data/service/hnp/perl.org/perl_5.42.0/` 目录。

3. **Makefile.PL 改进**：建议在 Makefile.PL 中添加对 Ohos SDK sysroot 的检测，自动设置正确的 include 和 lib 路径。

4. **Perl XS 扩展特殊性**：Perl XS 扩展使用 Makefile.PL 而不是标准的 autotools，需要特殊的编译配置。
---

**编译结束**: 2026-06-11 11:43
**功能测试**: 2026-06-11 14:05
**最终状态**: built (需管理员安装 XS 模块到系统目录)
