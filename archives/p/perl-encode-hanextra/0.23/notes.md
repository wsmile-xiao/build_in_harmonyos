# perl-encode-hanextra 0.23 适配笔记

## 编译环境
- 构建系统: makefile (Perl XS 模块，使用 Makefile.PL)
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built (SELinux 平台限制导致功能测试无法在用户路径完成)

## 编译步骤

1. **初始化构建环境**
   ```bash
   SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
   python3 "$SKILL_ROOT/scripts/ohc-run.py" init-build perl-encode-hanextra 0.23
   source .build-context-perl-encode-hanextra-0.23
   cd $BUILD_SRC_DIR
   ```

2. **生成 Makefile** (Perl XS 模块特殊处理)
   ```bash
   # 需要用 -I . 添加当前目录到 @INC，让 inc::Module::Install 可找到
   perl -I . Makefile.PL PREFIX=$DEFAULT_PREFIX \
     CCFLAGS="-D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -I$DEFAULT_PREFIX/include" \
     LDFLAGS="-L$DEFAULT_PREFIX/lib"
   ```

3. **编译**
   ```bash
   # LDDLFLAGS 需要使用 -nostdlib 绕过 libunwind
   make LDDLFLAGS="-shared -nostdlib -B$DEFAULT_PREFIX/lib -L$DEFAULT_PREFIX/lib -lc"
   ```

4. **安装到 staging**
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

5. **预编译包制作**
   ```bash
   python3 "$SKILL_ROOT/scripts/ohc-run.py" package perl-encode-hanextra 0.23
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | inc::Module::Install 找不到 | Makefile.PL 使用 inc:: 模块，默认 @INC 不含当前目录 | `perl -I . Makefile.PL` |
| 2 | errno.h 找不到 | Perl XS 默认 CCFLAGS 不含系统头文件路径 | CCFLAGS 显式添加 `-D_GNU_SOURCE -I$DEFAULT_PREFIX/include` |
| 3 | libunwind.a 找不到 | musl 系统无 libunwind，默认 LDDLFLAGS 会链接它 | `LDDLFLAGS="-shared -nostdlib ..."` |
| 4 | SELinux 限制 .so 无法加载 | 用户路径(hmdfs:s0)的.so无法被 Perl DynaLoader 加载 | 平台限制，需安装到系统 Perl 目录 |

## 源码修改

无补丁，仅通过编译参数适配。

## 依赖版本

- perl/5.42.0 (系统预装)
- Encode/3.21 (Perl 核心模块)
- enc2xs/2.25 (Encode 工具)

## 功能测试结果

### 结构验证（通过）

| 检查项 | 结果 |
|--------|------|
| HanExtra.pm 版本 | 0.23 ✅ |
| 编码别名数量 | 18 个 ✅ |
| HanExtra.so ELF 架构 | ELF64 AArch64 ✅ |
| 动态链接依赖 | 仅 libc.so ✅ |
| Perl XS boot 符号 | boot_Encode__HanExtra ✅ |
| 编码表完整性 | 21 种中文编码嵌入 ✅ |

### 支持的编码

HanExtra 扩展了以下中文编码：
- **Big5 变体**: big5-1984, big5-2003, big5ext, big5plus
- **台湾标准**: cns11643-1~7, cns11643-f, euc-tw
- **其他**: cccii, gb18030, unisys, unisys-sosi1, unisys-sosi2

### 运行时测试（SELinux 限制）

用户路径 `.so` 文件标签 `hmdfs:s0` 无法被 Perl DynaLoader 加载。
需安装到系统 Perl 目录 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/`。

### 对比验证

与系统 Encode.so 对比：
- ELF 结构一致（ELF64 AArch64）
- 依赖库一致（仅 libc.so）
- boot 符号格式正确

### 结论

编译成功，模块结构正确，可在鸿蒙平台使用（需系统目录安装）。

---

### SELinux 限制分析

**问题**: 用户路径下的 .so 文件无法加载，报错 "Permission denied"

**原因**: SELinux 标签差异
- 用户目录: `u:object_r:hmdfs:s0`
- 系统Perl目录: `u:object_r:hnp_file:s0`

**解决方案**:
- 需要将 Perl XS 模块安装到系统 Perl 目录 (`/data/service/hnp/perl.org/perl_5.42.0/lib/`)
- 系统 Perl 目录需要 `installs` 用户权限
- 预编译包安装脚本需要处理 SELinux 标签

**编译配置参数**:
- `perl -I . Makefile.PL PREFIX=$DEFAULT_PREFIX`
- `CCFLAGS="-D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -I$DEFAULT_PREFIX/include"`
- `LDDLFLAGS="-shared -nostdlib -B$DEFAULT_PREFIX/lib -L$DEFAULT_PREFIX/lib -lc"`

**编译依赖**: enc2xs, Encode 模块 (已满足)

**编译状态**: 成功，生成 HanExtra.so (11.8MB)
---

**编译结束**: 2026-06-10 20:54
**最终状态**: built
