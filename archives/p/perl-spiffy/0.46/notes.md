# perl-spiffy 0.46 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-01
- 验证日期: 2026-07-02
- 编译器: clang/clang++ (未使用，纯 Perl 模块)
- 状态: built (conan-verify 通过，待 CI upload 后标 published)

## 编译步骤

1. 从 CPAN 下载 Spiffy-0.46.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-spiffy 0.46
3. 运行 perl Makefile.PL INSTALL_BASE=/ 配置
4. 运行 make -j1 编译
5. 运行 make install DESTDIR=$staging 安装到 staging
6. 生成 Conan 配方：ohc-run.py conan-init perl-spiffy 0.46
7. 验证 Conan 配方：ohc-run.py conan-verify perl-spiffy 0.46
8. 运行上游测试套件：make test (32 文件 198 用例全部通过)
9. 上库自检：ohc-run.py submit perl-spiffy 0.46 (6/6 PASS)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 归档缺失 conanfile.py/conandata.yml | finish 流程异常中断 | 从 Conan 缓存恢复 ($CONAN_CACHE/p/perl-xxx/e/) |
| 2 | 归档缺失 manifest.yaml/notes.md/README.md | finish 流程异常中断 | 参考 perl-dbd-pg 模板手工创建 |
| 3 | test_package 缺失 MANIFEST.yml | CI L0e 门禁要求 | 创建 test_package/MANIFEST.yml 声明上游测试 |
| 4 | G2: PERL5LIB 路径计算错误 | Spiffy.pm 在 lib/perl5/ 下，多取了一层 dirname | `lib_dir = os.path.dirname(pm_files[0])` |
| 5 | G2: field 测试语法错误 | `field bar => { default => 99 }` 把 hash ref 当默认值 | 改为 `field bar => 99` (直接传标量) |
| 6 | G2: mixin 测试 `use MyMixin -mixin` 失败 | Perl `use` 编译时 `require MyMixin` 找不到 .pm 文件 | 改用 `use mixin 'MyMixin'` (Spiffy 重写了 mixin::import) |
| 7 | G2: super 测试 `use Parent -base` 失败 | 同上，`require Parent` 找不到文件 | 改用 `use base 'Parent'` (Spiffy 重写了 base::import) |
| 8 | 上库自检: manifest_complete FAIL | `_parse_yaml_simple` 是扁平解析器，不读嵌套字段 | 添加顶级 `build_system: perl` 字段 |
| 9 | 上库自检: packaging_present FAIL | 缺少 packaging/ 目录 | 从 Conan 包目录创建 tar.gz |

### 与 perl-dbd-pg 编译经验的对比

perl-dbd-pg 3.18.0 编译中遇到的关键问题及其在 perl-spiffy 中的适用性：

| perl-dbd-pg 问题 | perl-spiffy 适用性 | 说明 |
|-----------------|-------------------|------|
| 缺少 CRT 文件 (crti.o 等) | ❌ 不适用 | Spiffy 是纯 Perl 模块，无 C/XS 代码，不需要链接 |
| SELinux HMDFS 动态库加载限制 | ❌ 不适用 | Spiffy 只安装 .pm 文件，无 .so 动态库 |
| DBI::DBD 模块加载失败 | ❌ 不适用 | Spiffy 不依赖 DBI |
| 缺少 musl C 库头文件 | ❌ 不适用 | 纯 Perl 模块无需 C 头文件 |
| ExtUtils::MakeMaker 正常工作 | ✅ 适用 | 两者均使用 Makefile.PL 构建系统 |

**关键结论**: 纯 Perl 模块在鸿蒙平台上编译无需额外适配，ExtUtils::MakeMaker 完全兼容。
perl-dbd-pg 的经验主要适用于 XS/C 扩展模块，纯 Perl 模块只需标准 `perl Makefile.PL && make && make install` 流程。
但 Spiffy 的测试需要特别注意 Perl 的 `use` 语句在编译时执行的特点，inline package 测试需使用 Spiffy 重写的 `base::import` 和 `mixin::import`。

## 测试结果

### Conan 配方验证 (conan-verify)
- G0-G4 + L2/L4/L5: 全部 ✅ PASS
- Conan L1 测试: 6/6 通过 (模块加载、field、const、mixin、super、export)

### 上游测试套件 (make test)
- 32 个测试文件，198 个测试用例
- 全部通过 (1 个 skipped: release-pod-syntax.t)

### 上库自检 (submit)
- 6/6 PASS (manifest_complete, progress_closed, patches_valid, packaging_present, no_temp_files, test_report_present)

## 依赖版本

### 已存在
- perl: /data/service/hnp/perl.org/perl_5.42.0 (系统预装)

### 编译依赖
- perl (5.42.0)

## 编译产物

- **Spiffy.pm**: 15485 bytes，纯 Perl 模块文件
- **Spiffy.pod**: 18181 bytes，POD 文档
- **Spiffy/mixin.pm**: 26 bytes，mixin 子模块（stub 文件）

## 知识沉淀

### 平台发现
- 纯 Perl 模块在鸿蒙平台上编译无需任何适配
- ExtUtils::MakeMaker 完全兼容 OHOS 平台
- INSTALL_BASE=/ 参数可将模块安装到 DESTDIR/lib/perl5/ 标准路径
- Spiffy 重写了 base::import 和 mixin::import，inline package 测试需使用 `use base`/`use mixin` 语法
- `_parse_yaml_simple` 是扁平解析器，manifest.yaml 中的 build_system 需放在顶级

### 编译建议
- 纯 Perl 模块无需关注 CRT 文件缺失、SELinux 限制等 XS 模块特有问题
- 使用 INSTALL_BASE=/ 确保 Conan package() 可以正确收集产物
- test_package 应覆盖模块的核心功能（field、const、mixin、super、export）
- Perl one-liner 测试中，`use Module` 会在编译时 `require` 文件，inline package 需用 `use base`/`use mixin` 代替

---
**编译结束**: 2026-07-01
**验证完成**: 2026-07-02
**最终状态**: built (conan-verify 全门禁通过，上库自检 6/6 PASS)
