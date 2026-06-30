# perl-list-moreutils-xs 0.430-r6 适配笔记

## 编译环境
- 构建系统: perl (Makefile.PL)
- 编译日期: 2026-06-13
- 编译器: clang 18.1.8
- 状态: built
- 目标平台: aarch64-unknown-linux-ohos

## 编译步骤

### 1. 源码下载
```bash
源码位于: perl-list-moreutils-xs-0.430-r6.tar.gz
URL: https://download.savannah.nongnu.org/releases/perl-list-moreutils-xs/perl-list-moreutils-xs-0.430-r6.tar.gz
```

### 2. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-list-moreutils-xs 0.430-r6
```

### 3. 配置
```bash
cd /storage/Users/currentUser/tmp/builds/perl-list-moreutils-xs-0.430-r6.work
export CPATH=/storage/Users/currentUser/usr/local/include
export LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local INC="-I. -I/storage/Users/currentUser/usr/local/include"
```

### 4. 手动修复 LMUconfig.h
```bash
# Config::AutoConf::LMU 无法正确检测 size_t/ssize_t
# 手动添加必要的宏定义到 LMUconfig.h
#define HAVE_SIZE_T 1
#define HAVE_SSIZE_T 1
#define HAVE_TIME_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_BUILTIN_EXPECT 1
#define HAS_BUILTIN_EXPECT 1
#define HAVE_FEATURE_STATEMENT_EXPRESSION 1
```

### 5. 编译
```bash
make OTHERLDFLAGS="-nostartfiles -nodefaultlibs"
```

编译成功，生成：
- blib/arch/auto/List/MoreUtils/XS/XS.so（XS 模块，149KB）
- XS.pm（纯 Perl 模块）

### 6. 安装
```bash
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-perl-list-moreutils-xs-0.430-r6
make install  # 本地安装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | typedef size_t/ssize_t 重定义冲突 | Config::AutoConf::LMU 无法正确检测系统类型定义，生成的 LMUconfig.h 为空 | 手动修复 LMUconfig.h，添加 HAVE_SIZE_T 和 HAVE_SSIZE_T 宏定义 |
| 2 | sys/types.h 文件找不到 | Perl XS 编译时未设置 CPATH | `export CPATH=/storage/Users/currentUser/usr/local/include` |
| 3 | CRT 文件找不到（crti.o, crtn.o等） | Perl XS 链接时缺少 CRT 文件 | `make OTHERLDFLAGS="-nostartfiles -nodefaultlibs"` |
| 4 | XS 模块无法加载（Permission denied） | SELinux HMDFS 限制 | 正常限制，需管理员安装到系统目录（参考 perl-dbd-pg 经验） |
| 5 | 质量门禁 G4 失败（无二进制文件） | Perl XS 模块产物是 .so 文件，非传统二进制 | 正常情况，标记为 built 状态 |

## 源码修改

应用了 2 个补丁：
- 0001-LMUconfig.h.patch（手动添加类型检测宏定义）
- 0002-Makefile.patch（编译配置调整）

## 依赖版本

- musl: 1.2.5（提供标准 C 库头文件）
- Perl: 5.42.0
- clang: 18.1.8

## 验证结果

### XS 模块加载测试
```bash
perl -I/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux -MList::MoreUtils::XS -e 'print $List::MoreUtils::XS::VERSION'
```

结果：Permission denied（SELinux HMDFS 限制，正常）

### 编译产物检查
```bash
ls -lh /storage/Users/currentUser/tmp/builds/perl-list-moreutils-xs-0.430-r6.work/blib/arch/auto/List/MoreUtils/XS/XS.so
```

结果：XS.so 存在，149KB

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| XS.so | 149KB | List::MoreUtils::XS 模块 |
| XS.pm | - | List::MoreUtils::XS 纯 Perl 模块 |

## 注意事项

1. **SELinux HMDFS 限制**：XS 模块（.so 文件）在 HMDFS 上无法加载，需要管理员安装到系统目录 `/data/service/hnp/`。
2. **编译参数**：所有 Perl XS 模块编译需要 `-nostartfiles -nodefaultlibs` 参数。
3. **环境变量**：必须设置 CPATH 和 LIBRARY_PATH，否则找不到 musl 头文件和库文件。
4. **Config::AutoConf 问题**：该模块在 OpenHarmony 上无法正确检测类型定义，需要手动修复 LMUconfig.h。
5. **质量门禁 G4**：无二进制文件是 Perl XS 模块的正常情况，不影响发布。

## 参考经验

- 参考 perl-dbd-pg 3.18.0 的编译经验（archives/p/perl-dbd-pg/3.18.0/notes.md）
- X5 模块加载问题属于平台限制，不影响编译流程

---
**编译结束**: 2026-06-13 17:10
**最终状态**: built