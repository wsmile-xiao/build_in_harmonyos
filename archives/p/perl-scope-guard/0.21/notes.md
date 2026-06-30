# perl-scope-guard 0.21 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- Perl 版本: 5.42.0 (/data/service/hnp/bin/perl)
- 状态: published

## 编译步骤

Scope::Guard 是纯 Perl 模块，无 XS/C 代码，编译流程简单：

```bash
# 1. 从 CPAN 下载源码
# 2. 配置
perl Makefile.PL INSTALLDIRS=site
# 3. 编译
make -j1
# 4. 安装到 staging
make install DESTDIR=$TEST_PREFIX
# 5. 测试
make test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py 的 generate() 使用 AutotoolsToolchain + `-static` | 自动化生成时为满足 R26 添加了静态链接配置，但纯 Perl 模块不需要 | 移除 generate() 方法，参考 perl-dbd-pg 经验：纯 Perl 模块无需特殊链接参数 |
| 2 | package() 使用复杂 glob 从 DESTDIR staging 提取 .pm 文件 | 自动生成逻辑过于复杂，依赖 site_perl 路径解析 | 简化为直接从 blib/lib 复制 .pm 到 lib/perl5 |
| 3 | package_info() 硬编码 `site_perl/5.42.0` 路径 | 版本号嵌入路径导致跨版本不兼容 | 改为泛化路径 lib/perl5 |
| 4 | test_package 包含 CMakeLists.txt 和 test.c | 自动生成时按 C/C++ 模板创建，但纯 Perl 模块不需要 | 删除 C/C++ 文件，test_package 直接用 perl 命令测试 |
| 5 | manifest.yaml 末尾有损坏的重复内容 | 模板渲染时的截断/拼接错误 | 重写 manifest.yaml |
| 6 | 缺少根目录 README.md 和 manifest.yaml | 归档时未生成软件级文件 | 补充创建 |

## 源码修改

无补丁、无源码修改。Scope::Guard 是纯 Perl 模块，原始源码在鸿蒙平台完全兼容。

## 依赖版本

### 编译依赖
- Perl 5.42.0 (系统预装，路径 /data/service/hnp/bin/perl)
- 无其他编译依赖（纯 Perl 模块，无 XS/C 代码）

### 运行时依赖
- Perl 5.42.0
- 无其他运行时依赖

## 验证结果

### make test 结果
```bash
t/guard.t ........ ok
t/new.t .......... ok
t/scope_guard.t .. ok
All tests successful.
Files=3, Tests=54,  0 wallclock secs
Result: PASS
```

### Staging 验证
```bash
$ PERL5LIB=... perl -MScope::Guard -e 'print $Scope::Guard::VERSION'
0.21
```

### Conan 验证（修复后重新验证）
```bash
$ conan create . --user ohpcd --channel stable -pr:h ohos-aarch64 -pr:b ohos-aarch64
# G0 ✅ G1 ✅ G2 ✅ G3 ✅ G4 ✅ L2 ✅ L4 ✅ L5 ✅
# test_package 三项测试全部通过:
#   Scope::Guard loaded successfully: OK
#   Version OK
#   Functional OK (新增: guard 作用域触发功能测试)
```

### 鸿蒙平台功能测试（13 项，全部 PASS）
| # | 测试项 | 结果 |
|---|--------|------|
| 1 | 模块加载 | ✅ |
| 2 | 版本验证 (0.21) | ✅ |
| 3 | guard() block 语法 | ✅ |
| 4 | new() 构造器语法 | ✅ |
| 5 | scope_guard() code ref 语法 | ✅ |
| 6 | dismiss() 取消守卫 | ✅ |
| 7 | dismiss(0) 重新启用 | ✅ |
| 8 | 异常情况触发 (die) | ✅ |
| 9 | 多个守卫全部触发 | ✅ |
| 10 | 闭包捕获词法变量 | ✅ |
| 11 | 文件句柄清理 | ✅ |
| 12 | 嵌套作用域守卫 | ✅ |
| 13 | void context 异常检测 | ✅ |

总计: 67 项测试全部通过（54 项 make test + 13 项功能测试），0 失败。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/Scope/Guard.pm | 3794 bytes | 核心模块 — 词法作用域资源管理 |

## 注意事项

1. 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名，不受鸿蒙 CRT 文件缺失影响。
2. 参考 perl-dbd-pg 编译经验：纯 Perl 模块在鸿蒙平台无需 `-nostartfiles -nodefaultlibs -lc` 等特殊链接参数。
3. conanfile.py 不包含 generate() 方法，因为纯 Perl 模块不涉及 C/C++ 编译，无需工具链配置。
4. package_info() 设置 PERL5LIB 环境变量，确保消费者通过 conanrun 环境自动获取正确的 Perl 模块搜索路径。
5. test_package 使用 subprocess 直接调用 perl 命令进行测试，不依赖 CMake/C++ 编译。

---

**编译结束**: 2026-06-29 15:28
**文档更新**: 2026-06-30 10:37
**最终状态**: published
