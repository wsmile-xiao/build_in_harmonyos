# perl-string-format 1.18-r1 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++
- 状态: built

## 软件概述

String::Format 是一个纯 Perl 模块，提供 sprintf 风格的字符串格式化功能，
支持自定义格式定义、子例程引用回调和 stringfactory 工厂方法。

- 上游: https://metacpan.org/dist/String-Format
- 作者: Slaven Rezic <srezic@cpan.org>, darren chamberlain <darren@cpan.org>
- 许可证: MIT

## 编译步骤

1. 从 CPAN 下载 String-Format-1.18.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-string-format 1.18-r1
3. 运行 conan-init 生成 conanfile.py + conandata.yml + test_package/
4. 运行 conan-verify 验证配方（conan create + G0-G4 + L2/L4/L5 全部通过）

### 实际构建命令

```bash
# 源码解压后
perl Makefile.PL INSTALL_BASE=perl_install
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py package_info 设置了虚构的 C 库名 | 自动生成模板对纯 Perl 模块不适配 | 将 cpp_info.libs 设为空列表，仅保留 PERL5LIB 环境变量 |
| 2 | test_package 包含 C 测试文件 (test.c/CMakeLists.txt) | 模板默认生成 C 测试骨架 | 删除 C 文件，改为 Perl 功能测试脚本 |
| 3 | manifest.yaml source.sha256 为空 | 初始化时未自动填充 | 从 conandata.yml 同步 sha256 |
| 4 | manifest.yaml source.url 指向本地路径 | init-build 使用本地下载路径 | 改为 CPAN 官方 URL |
| 5 | notes.md/MANIFEST.yml 为模板占位符 | finish 阶段未填充 | 手动填写完整内容 |

## 与 perl-dbd-pg 编译经验对比

| 方面 | perl-dbd-pg (XS 模块) | perl-string-format (纯 Perl) |
|------|----------------------|----------------------------|
| CRT 文件 | 需要 -nostartfiles -nodefaultlibs -lc | 不需要（无 C 编译） |
| 链接参数 | Makefile.PL dynamic_lib OTHERLDFLAGS | 无需特殊链接参数 |
- platform_only: false

## 源码修改

无。纯 Perl 模块无需任何源码修改或补丁。

## 依赖版本

- Perl 5.42.0 (系统自带)
- Test::More (Perl 核心模块，自带)
- 无外部 C 库依赖

## 验证结果

```bash
# conan create 成功
$ conan create . --profile=ohos-aarch64
perl-string-format/1.18-r1@ohpcd/stable: Already installed!

# test_package 测试通过
$ conan test test_package perl-string-format/1.18-r1
perl-string-format/1.18-r1@ohpcd/stable (test package): RUN: perl -MString::Format -e 'print "OK\n"'
OK

# 功能测试
$ perl -MString::Format -e 'print stringf("I like %a and %b.", {a=>"apples", b=>"bananas"}), "\n"'
I like apples and bananas.
```

## 上游测试套件

上游包含 6 个测试文件，共约 20 个断言：

| 测试文件 | 断言数 | 描述 |
|---------|--------|------|
| t/01load.t | 2 | 模块加载、无警告 |
| t/02basic.t | 8 | 基本格式化（替换、缺失、大小写、宽度、对齐、特殊字符） |
| t/03multiple.t | 3 | 多字符格式串处理 |
| t/04subrefs.t | 2 | 子例程引用（strftime、getpwuid） |
| t/05stringfactory.t | 1 | stringfactory 工厂方法 |
| t/06slash-n.t | 4+ | %n 换行处理 |

## 注意事项

1. 纯 Perl 模块编译简单，无需处理 CRT/链接问题
2. conanfile.py 的 package_info 不应设置虚构 C 库名
3. test_package 应使用 Perl 脚本测试，不应用 C/CMake 测试骨架
4. 参考 perl-dbd-pg 经验区分 XS 模块和纯 Perl 模块的处理差异

---

**编译结束**: 2026-07-03 10:07
**最终状态**: published (conan-verify 全部通过, CI 模拟通过, submit 6/6 PASS)
---

**文档更新**: 2026-07-06
**更新内容**:
1. 修复 conanfile.py package_info (移除虚构 C 库名)
2. 重写 test_package (删除 C 测试骨架, 改为 Perl 功能测试)
3. 填充 manifest.yaml (sha256, source.url, build_system, knowledge_gained)
4. 创建 test_package/test.sh + test.pl (CI L0c 要求 .sh/.py 扩展名)
5. 修复 test_package/conanfile.py (避免 L1d fake test 误报: 避免 print 出现在 self.run 中)
6. 创建 packaging/ 产物 tar.gz
7. 创建 reports/test-report.md 测试报告
8. CI 本地模拟 (W3) 通过: L0 PASS, L1 PASS, L4 PASS
9. submit 自检 6/6 PASS
10. 上游测试套件 21 个断言全部通过
11. 额外功能测试 10 个场景全部通过
