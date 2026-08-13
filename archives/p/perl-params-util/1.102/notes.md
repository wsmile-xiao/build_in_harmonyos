# perl-params-util 1.102 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 Params-Util-1.102.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-params-util 1.102
3. 运行 perl Makefile.PL 配置
4. 修改 Makefile 添加 musl 头文件路径和 CRT 链接参数
5. 运行 make 编译
6. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging
7. 生成 Conan 配方 (conan-init)
8. 验证 Conan 配方 (conan-verify) — 全部门禁通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：缺少 crti.o, crtn.o, crtbeginS.o, crtendS.o | 鸿蒙系统缺少 CRT 文件 | 在 Makefile 的 LDDLFLAGS 中添加 `-nostartfiles -nodefaultlibs -L$MUSL_PREFIX/lib -lc` |
| 2 | 编译错误：缺少 sys/types.h 等系统头文件 | 鸿蒙系统缺少标准 C 库头文件 | 在 Makefile 的 CCFLAGS 中添加 `-I$MUSL_PREFIX/include` (musl 头文件路径) |
| 3 | XS 模块运行时加载失败 (Permission denied) | SELinux HMDFS 限制动态库加载 | 使用纯 Perl 回退模式 `PERL_PARAMS_UTIL_PP=1`；XS .so 需安装到系统目录 |

## 与 perl-dbd-pg 编译经验对比

| 方面 | perl-dbd-pg 3.18.0 | perl-params-util 1.102 |
|------|---------------------|------------------------|
| 构建系统 | Perl Makefile.PL | Perl Makefile.PL |
| CRT 绕过 | `-nostartfiles -nodefaultlibs -lc` | 相同方案 |
| musl 头文件 | 需要 (stdio.h, ctype.h 等) | 需要 (sys/types.h 等) |
| 链接参数注入方式 | `dynamic_lib => { OTHERLDFLAGS => ... }` (Makefile.PL) | `make OTHERLDFLAGS` 命令行参数 (不同方式) |
| SELinux 限制 | XS .so 无法从用户目录加载 | 相同问题 |
| 纯 Perl 回退 | 无 (DBI::PurePerl 是独立模式) | 有 (PERL_PARAMS_UTIL_PP=1) |
| 外部依赖 | libpq, DBI | 无 |

## 依赖版本

### 已存在
- musl C 库头文件: $MUSL_PREFIX/include (sys/types.h 等)
- musl C 库: $MUSL_PREFIX/lib

### 编译依赖
- musl C 库头文件（提供 sys/types.h 等系统头文件）

## 编译产物

- **Util.so**: 21KB，ELF 64-bit ARM64 共享对象
- **Util.pm**: Perl 模块文件
- **PP.pm**: 纯 Perl 回退模块文件

## 知识沉淀

### 平台发现
- 鸿蒙系统缺少 CRT 文件（crti.o, crtn.o 等）
- 链接 Perl XS 模块需要 `-nostartfiles -nodefaultlibs -lc` 参数
- SELinux HMDFS 限制动态库加载到用户目录
- Params::Util 提供纯 Perl 回退，可作为 XS 不可用时的替代方案

### 编译建议
- Perl XS 模块编译需要完整的 C 库头文件支持
- 修改生成的 Makefile（非 Makefile.PL）的 CCFLAGS 添加 musl 头文件路径
- 修改生成的 Makefile 的 LDDLFLAGS 添加 CRT 绕过链接参数
- 参考 perl-dbd-pg 编译经验可直接复用 CRT 绕过方案

## 后续修复与完善 (2026-07-06)

### 问题发现
初始编译完成后，归档目录缺失关键文件：
- conanfile.py (存在于 conan 缓存但未复制到归档)
- conandata.yml (同上)
- test_package/ (conan-verify 时存在但后续丢失)
- manifest.yaml, notes.md, README.md (从未创建)

### 修复措施
1. 从 conan 缓存恢复 conanfile.py 和 conandata.yml
2. 创建 test_package/conanfile.py + test_params_util.sh (L1 测试脚本化)
3. 创建 test_package/MANIFEST.yml
4. 创建 manifest.yaml (含 patch_generation 和 patch_classification)
5. 创建 notes.md (编译笔记)
6. 创建 README.md (软件描述)
7. 创建 packaging/ 目录 (.packaged + Util.so + tar.gz)
8. 修复 manifest.yaml: 添加顶层 build_system 字段

### 验证结果
- conan-verify: 全部 8 道门禁通过 (G0-G4 + L2/L4/L5)
- CI 模拟 (build_and_test.sh): L0-L5 全部通过 (1 success, 0 failed)
- PP 测试套件: 932/932 通过
- 综合功能测试: 44/44 通过
- submit 自检: 6/6 PASS
- 知识图谱: E173 命中 (Perl XS CRT 缺失)

### 状态变更
- 初始状态: built (conan-verify 通过但归档不完整)
- 最终状态: built (归档完整，CI 模拟通过，submit 自检 6/6，待 CI upload 后更新为 published)

---
**编译结束**: 2026-07-03 16:57
**归档完善**: 2026-07-06
**最终状态**: built (编译成功，conan-verify 全部门禁通过，CI 模拟通过，submit 自检 6/6 PASS，待 CI upload)
 6/6 PASS，待 CI upload)
