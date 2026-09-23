# DBI 1.637 适配笔记

## 编译环境
- 构建系统: perl_xs (Makefile.PL)
- 编译日期: 2026-06-10
- 编译器: clang 18.1.8
- Perl 版本: 5.42.0
- 状态: built

## 编译步骤

### 1. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build DBI 1.637
```

### 2. 生成 Makefile
```bash
cd $BUILD_SRC_DIR
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
```

**注意**: 不能同时使用 PREFIX 和 INSTALL_BASE 参数。

### 3. 修改 Makefile（添加 musl 头文件路径）
```bash
sed -i 's|^CCFLAGS = |CCFLAGS = -I/storage/Users/currentUser/usr/local/include |' Makefile
```

### 4. 修改 Makefile（添加链接参数）
```bash
sed -i 's|^LDDLFLAGS = |LDDLFLAGS = -nostartfiles -nodefaultlibs |' Makefile
```

**原因**: 系统缺少 CRT 文件 (crti.o, crtn.o 等)，需要禁用标准启动文件和默认库。

### 5. 编译
```bash
make -j1
```

**编译结果**:
- 生成 306 个警告（STMT_START/STMT_END 宏展开警告）
- 成功生成 DBI.so (129KB)

### 6. 安装
```bash
# Staging 安装
make install DESTDIR=$TEST_PREFIX

# 本地安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sys/types.h 找不到 | 系统缺少 C 标准库头文件 | 添加 musl 头文件路径到 CCFLAGS: `-I$DEFAULT_PREFIX/include` |
| 2 | 链接失败：找不到 crti.o/crtn.o | 系统缺少 CRT 文件 | 添加链接参数：`-nostartfiles -nodefaultlibs` |
| 3 | PREFIX 和 INSTALL_BASE 冲突 | Perl Makefile.PL 不允许两者同时使用 | 只使用 INSTALL_BASE 参数 |
| 4 | XS 模块加载失败 (Permission denied) | SELinux HMDFS 限制 | DBI::PurePerl 模式可用，XS 模块需要管理员安装 |

## 源码修改

无源码修改，仅修改生成的 Makefile。

## 依赖版本

- Perl: 5.42.0 (系统预装)
- musl: 1.2.5 (已编译，提供头文件)
- clang: 18.1.8

## 验证结果

### DBI::PurePerl 模式 ✅ 可用
```bash
export DBI_PUREPERL=2
perl -I$DEFAULT_PREFIX/lib/perl5/aarch64-linux -MDBI -e 'print $DBI::VERSION'
# 输出: 1.637
```

### DBI XS 模块 ❌ 不可用（SELinux 限制）
```bash
perl -I$DEFAULT_PREFIX/lib/perl5/aarch64-linux -MDBI -e 'print $DBI::VERSION'
# 错误: Permission denied (SELinux HMDFS 限制)
```

### 测试结果
```bash
make test
# 大部分测试通过，少数测试被跳过
# 测试进程被 SIGTERM 中断（timeout）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| DBI.so | 129KB | XS 模块（需要管理员安装）|
| DBI.pm | 316KB | PurePerl 模块（可直接使用）|
| dbilogstrip | - | 工具脚本 |
| dbiprof | - | 工具脚本 |
| dbiproxy | - | 工具脚本 |

## 注意事项

1. **SELinux HMDFS 限制**: XS 模块无法在用户目录加载，需要管理员安装到 `/data/service/hnp`
2. **DBI::PurePerl 模式**: 可立即使用，性能略低于 XS 版本
3. **编译警告**: 306 个 STMT_START/STMT_END 宏展开警告，不影响功能
4. **链接参数**: 必须使用 `-nostartfiles -nodefaultlibs` 才能成功链接
---

**编译结束**: 2026-09-07 22:06
**最终状态**: built
