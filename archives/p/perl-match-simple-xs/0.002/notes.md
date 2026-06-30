# perl-match-simple-xs 0.002 编译笔记

**编译日期**: 2026-06-15
**编译器**: Perl 5.42.0 + clang
**构建系统**: Module::Build (Perl XS)

---

## 编译过程

### Step 1: 源码下载

从 CPAN 下载源码包：
```
match-simple-XS-0.002.tar.gz
```

### Step 2: 构建配置

Perl XS 模块使用 Perl Module::Build 构建系统：
```bash
perl Build.PL
./Build
./Build test
./Build install
```

### Step 3: 编译结果

编译成功，生成以下产物：
- XS.so: Perl XS 扩展模块
- XS.pm: Perl 模块文件

### Step 4: 打包

预编译包制作完成：
- perl-match-simple-xs-0.002-ohos-aarch64.tar.gz (91KB)
- perl-match-simple-xs-0.002-ohos-aarch64-debug.tar.gz (20KB)

---

## 问题与解决

### 问题 1: G0 验证失败

**现象**: G0 干净构建验证时 configure 失败
**原因**: Perl XS 模块没有 configure 脚本，使用 Module::Build
**解决**: 这是预期行为，G0 验证脚本需要识别 Perl XS 构建系统

### 问题 2: SELinux HMDFS 限制

**现象**: XS.so 从 ~/usr/local/lib 加载失败
**原因**: SELinux domain 只允许加载 hnp_file 类型文件
**解决**: 需安装到系统目录 /data/service/hnp/

---

## 知识沉淀

1. Perl XS 模块构建系统识别
2. SELinux HMDFS 限制处理方案

---

**编译结束**: 2026-06-15 22:10
**最终状态**: built（编译成功，需管理员安装）