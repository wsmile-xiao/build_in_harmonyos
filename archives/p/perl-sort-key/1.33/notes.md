# perl-sort-key 1.33 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 Sort-Key-1.33.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-sort-key 1.33
3. 修改 Makefile.PL 添加链接参数（绕过 CRT 文件缺失）
4. 运行 perl Makefile.PL INSTALLDIRS=site 配置
5. 运行 make -j1 编译
6. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：缺少 crti.o, crtn.o, crtbeginS.o, crtendS.o | 鸿蒙系统缺少 CRT 文件 | 在 Makefile.PL 中添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }` |
| 2 | SELinux HMDFS 限制 | 动态库加载受限 | 需安装到系统目录 /data/service/hnp |

## 参考：perl-dbd-pg 编译经验

本软件的编译参考了 perl-dbd-pg 3.18.0 的编译经验：
- 两者都是 Perl XS 模块，使用 ExtUtils::MakeMaker 构建系统
- 都遇到相同的 CRT 文件缺失问题
- 解决方案完全一致：在 Makefile.PL 中添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }`

## 依赖版本

### 已存在
- perl 5.42.0 (提供 perl 解释器和 ExtUtils::MakeMaker)

### 编译依赖
- perl (提供 perl 解释器和 ExtUtils::MakeMaker)

## 编译产物

- **Key.so**: 39KB，ELF 64-bit ARM64 共享对象 (XS 模块)
- **Key.pm**: Perl 模块文件 (8.8KB)
- **Sort/Key/Multi.pm**: 多键排序模块 (3.1KB)
- **Sort/Key/Maker.pm**: 排序生成器模块 (3.0KB)
- **Sort/Key/Types.pm**: 类型定义模块 (5.3KB)
- **Sort/Key/Register.pm**: 注册模块 (2.1KB)
- **Sort/Key/Natural.pm**: 自然排序模块 (6.9KB)

## 知识沉淀

### 平台发现
- 鸿蒙系统缺少 CRT 文件（crti.o, crtn.o 等），与 perl-dbd-pg 编译时发现的一致
- 链接 Perl XS 模块需要 `-nostartfiles -nodefaultlibs -lc` 参数
- SELinux HMDFS 限制动态库加载到用户目录

### 编译建议
- Perl XS 模块编译需要完整的 C 库头文件支持
- Makefile.PL 中可通过 `dynamic_lib` 参数添加链接选项
- 需要 ELF 签名才能在鸿蒙系统执行

## 功能测试结果 (2026-07-02)

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 编译验证 | ✅ PASS | configure + make + install 全部成功 |
| Conan 配方验证 | ✅ PASS | G0-G4, L2, L4, L5 全门禁通过 |
| ELF 文件验证 | ✅ PASS | 64-bit ARM64, libc.so 依赖, BIND_NOW |
| 安全属性 | ✅ PASS | Full RELRO, NX Stack, PIE |
| Perl 语法检查 | ✅ PASS | 6 个 .pm 文件全部 syntax OK |
| 上游测试套件 | ⚠️ BLOCKED | SELinux E046: .so 从 HMDFS 加载被拒绝 |
| 运行时功能测试 | ⚠️ BLOCKED | 需安装到系统目录 /data/service/hnp |

**结论**: 编译成功，配方验证通过，可标记 published。运行时测试受 SELinux HMDFS 限制，
需通过 CI 流水线安装到系统目录后执行。

---
**编译结束**: 2026-07-01 10:05
**最终状态**: published (conan-verify 全门禁通过)
