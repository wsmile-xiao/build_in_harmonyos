# perl-crypt-eksblowfish 0.009-r15 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03（首次），2026-07-09（CI 修复）
- 编译器: clang/clang++
- 状态: built (conan-verify 全部门禁通过)

## 编译步骤

1. 从 CPAN 下载 Crypt-Eksblowfish-0.009.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-crypt-eksblowfish 0.009-r15
3. 修改 Makefile.PL：替换 Module::Build passthrough 为独立 ExtUtils::MakeMaker 版本，清理 ldflags 中的 -fstack-protector-strong（ld.lld 不支持，E137）
4. 设置 CPATH/LIBRARY_PATH 指向 OHOS SDK sysroot（musl 头文件）
5. 运行 perl Makefile.PL 生成 Makefile
6. 运行 make 编译
7. 从 blib/ 目录复制产物到 package

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Can't locate Module/Build.pm` | Module::Build 在 Perl 5.39+ 已从核心模块移除，CI worker (Perl 5.42.0) 上不可用 | 替换 Build.PL (Module::Build) 为 Makefile.PL (ExtUtils::MakeMaker)，ExtUtils::MakeMaker 仍是核心模块 |
| 2 | 链接错误：ld.lld 不识别 -fstack-protector-strong | OHOS 使用 ld.lld，不支持 GCC 特有的 -fstack-protector-strong 标志 (E137) | 在 Makefile.PL 中修改 %Config 清理 ldflags/lddlflags |
| 3 | 缺少 C 库头文件 | 鸿蒙系统默认头文件路径不包含 musl 头文件 | 设置 CPATH 指向 OHOS SDK sysroot 的 usr/include |
| 4 | 缺少 Perl 模块路径 | ExtUtils::MakeMaker 需要找到已安装的 Perl 模块 | 设置 PERL5LIB 包含用户安装路径和系统路径 |
| 5 | SELinux HMDFS 限制 | 动态库加载受限（hmdfs:s0 上下文被 dlopen 拒绝） | 需安装到系统目录 /data/service/hnp |
| 6 | R6 违规：运行时修改生成的 Build 脚本 | 原配方在 build() 中直接修改生成的 Build 脚本 | 创建 Makefile.PL 补丁替代运行时修改 |
| 7 | R32/R33 违规 | 原配方缺少 OS 检查且使用 os.environ | 添加 OS 检查和使用 buildenv_info |
| 8 | R34 空壳测试 | test_package 仅加载模块不调用 API | 添加 Blowfish->encrypt() 加密调用 |
| 9 | R3 手动补丁 | manifest.yaml 标记为 manual-diff | 使用 refresh-patch --auto 生成，标记为 auto |

## 依赖版本

### 已存在
- Perl: 5.42.0 (aarch64-linux, /data/service/hnp/perl.org/perl_5.42.0/)
- musl C 库头文件: OHOS SDK sysroot (stdio.h, ctype.h, sys/types.h 等)
- ExtUtils::MakeMaker: Perl 核心模块（始终可用）
- Class::Mix: 0.001 (用户安装，运行时依赖)
- MIME::Base64: 2.21+ (Perl 核心)
- XSLoader: Perl 核心

### 编译依赖
- OHOS SDK sysroot（提供 musl C 库头文件）
- Perl 5.42.0（提供 perl 二进制和核心模块）

## 编译产物

- **Eksblowfish.so**: 39KB，ELF 64-bit ARM64 共享对象
  - NEEDED: libc.so
  - 安全特性: NX + PIE (DYN) + RELRO + BIND_NOW
  - 导出符号: boot_Crypt__Eksblowfish
- **Eksblowfish.pm**: 主模块文件 (4565 bytes)
- **Bcrypt.pm**: bcrypt 哈希实现 (5013 bytes)
- **Blowfish.pm**: 标准 Blowfish 加密 (4061 bytes)
- **Family.pm**: 密码族管理 (6410 bytes)
- **Subkeyed.pm**: 子密钥支持 (6935 bytes)
- **Uklblowfish.pm**: 无密钥 Blowfish (5729 bytes)

## 构建系统切换说明（Module::Build → ExtUtils::MakeMaker）

### 背景
Perl 5.39.0 起，Module::Build 从 Perl 核心模块中移除。CI worker 使用 Perl 5.42.0，
不再包含 Module::Build。原 Build.PL 依赖 Module::Build，导致 CI 构建失败：
`Can't locate Module/Build.pm in @INC`

源码自带的 Makefile.PL 是 Module::Build::Compat 生成的 passthrough 脚本，
仍然依赖 Module::Build，不能直接使用。

### 方案
编写独立的 ExtUtils::MakeMaker 版 Makefile.PL，替换 passthrough 脚本：
- 使用 `use ExtUtils::MakeMaker; WriteMakefile(...)` 替代 `Module::Build->new()`
- 在 WriteMakefile 之前修改 `%Config{lddlflags}` 和 `%Config{ldflags}` 清理 -fstack-protector-strong
- 构建命令从 `perl Build PL && perl Build` 改为 `perl Makefile.PL && make`
- blib/ 输出结构相同，package() 方法无需修改
- 通过 `MY::c_o` postamble 覆盖 `.c$(OBJ_EXT)` 规则，添加 `-o $@` 修正子目录 .xs 文件的 .o 输出路径

## 知识沉淀

### 平台发现
- Module::Build 在 Perl 5.39+ 已从核心模块移除（重要！）
- ExtUtils::MakeMaker 仍然是核心模块，是 Perl XS 模块的推荐构建系统
- OHOS ld.lld 不支持 GCC 的 -fstack-protector-strong 标志 (E137)
- 修改 %Config 可有效清理链接器标志（ExtUtils::MakeMaker 读取 %Config）
- Makefile.PL 补丁方式优于运行时修改生成的 Makefile（符合 R6 规则）
- SELinux 限制：hmdfs:s0 上下文的 .so 文件无法通过 dlopen 加载

### 编译建议
- Perl XS 模块优先使用 ExtUtils::MakeMaker (Makefile.PL) 而非 Module::Build (Build.PL)
- 通过修改 %Config 清理不兼容的链接器标志是推荐做法
- CPATH/LIBRARY_PATH 设置是 OHOS 平台 Perl XS 编译的通用模式
- 需要 ELF 签名才能在鸿蒙系统执行

### 上库评估
- ✅ conanfile.py 完整且通过 conan-verify (G0-G4, L2-L5)
- ✅ conandata.yml 包含源码 URL、SHA256 和补丁声明
- ✅ test_package/ 包含 conanfile.py 和 MANIFEST.yml
- ✅ patches/ 包含 0001-Makefile.PL.patch
- ✅ manifest.yaml 包含完整编译元数据
- ✅ notes.md 包含编译笔记和知识沉淀
- ✅ R3: 补丁通过 refresh-patch --auto 生成
- ✅ R6: 补丁源文件 (Makefile.PL)，不修改生成文件
- ✅ R27: 依赖引用使用 @ohpcd/stable（无外部依赖）
- ✅ R28: test_package/ 存在
- ✅ R32: settings.os 判断使用 `in ("Linux", "OHOS")`
- ✅ R33: 使用 buildenv_info，不裸用 os.environ
- ✅ R34: test_package 调用 Blowfish->encrypt() 加密 API

---
**编译结束**: 2026-07-03 11:54
**最终状态**: built (编译成功，产物完整)
**归档完善**: 2026-07-09 (CI 修复: Module::Build→ExtUtils::MakeMaker, AI review 全部修复)
**测试完成**: 2026-07-09 (conan-verify PASS, 功能测试完成，SELinux 限制已记录)
