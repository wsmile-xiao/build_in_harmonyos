# perl-role-basic 0.16 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- Perl版本: 5.42.0
- 状态: published

## 编译步骤

1. 从 CPAN 下载 Role-Basic-0.16.tar.gz
2. 初始化编译环境：`ohc-run.py init-build perl-role-basic 0.16`
3. 运行 `perl Makefile.PL INSTALLDIRS=site` 配置
4. 运行 `make -j1` 编译
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
6. 运行 `make test` 执行测试（304 个测试全部通过）
7. 生成 Conan 配方：`ohc-run.py conan-init perl-role-basic 0.16`
8. 验证配方：`ohc-run.py conan-verify perl-role-basic 0.16`（全部门禁通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 中残留 C/C++ 文件 | conan-init 模板自动生成 CMakeLists.txt 和 test.c | 手动删除，替换为 Perl smoke test |
| 2 | notes.md/manifest.yaml 未填充 | finish 脚本自动生成模板但未由 AI 填充 | 参考 perl-dbd-pg 经验手动填充 |
| 3 | smoke test 中 `Role::Basic->can('with')` 返回 0 | `with` 关键字导出到调用者命名空间而非 Role::Basic 包本身 | 修改 smoke test 测试实际角色组合功能 |
| 4 | conanfile.py package() 需保留 Role/ 子目录结构 | Perl 模块按命名空间组织，需保持目录层次 | 使用 glob 遍历 staging 中的 .pm/.pod 文件，从 Role/ 前缀开始复制 |

## 源码修改

无补丁。Role::Basic 是纯 Perl 模块，无需修改源码即可在鸿蒙平台编译运行。

## 依赖版本

### 运行依赖
- perl 5.42.0（系统预装）

### 编译依赖
- 无额外依赖（纯 Perl 模块）

## 验证结果

```bash
# make test 结果
t/00-load.t .................................... ok
t/basic.t ...................................... ok
t/bugs.t ....................................... ok
t/composition.t ................................ ok
t/exceptions.t ................................. ok
t/internals.t .................................. ok
t/moose/003_apply_role.t ....................... ok
t/moose/004_role_composition_errors.t .......... ok
t/moose/005_role_conflict_detection.t .......... ok
t/moose/011_overriding.t ....................... ok
t/moose/012_method_exclusion_in_composition.t .. ok
t/moose/013_method_aliasing_in_composition.t ... ok
t/moose/014_more_alias_and_exclude.t ........... ok
t/moose/032_roles_and_method_cloning.t ......... ok
t/moose/033_role_exclusion_and_alias_bug.t ..... ok
t/moose/043_conflict_many_methods.t ............ ok
All tests successful.
Files=16, Tests=304,  3 wallclock secs
Result: PASS

# 模块加载验证
perl -MRole::Basic -e 'print Role::Basic->VERSION' → 0.16

# Conan smoke test
✅ Role::Basic loaded successfully
✅ Role composition (with) works correctly
✅ requires constraint works correctly
✅ Method exclusion (-excludes) works correctly
✅ Method aliasing (-alias) works correctly
```

## 知识沉淀

### 平台发现
- 纯 Perl 模块（无 XS 代码）在鸿蒙平台可直接编译，无需特殊适配
- 与 perl-dbd-pg 等 XS 模块不同，纯 Perl 模块无需处理 CRT 文件缺失、链接参数等问题
- ExtUtils::MakeMaker 构建系统在鸿蒙平台工作正常

### 编译建议
- 纯 Perl 模块使用 `perl Makefile.PL INSTALLDIRS=site` + `make` + `make install` 标准流程
- test_package 应使用 Perl smoke test 而非 C/C++ 测试框架
- Conan 配方的 package_info 应设置 `PERL5LIB` 环境变量以便模块加载
- Role::Basic 的 `with` 关键字导出到调用者命名空间，smoke test 应测试实际角色组合而非 `can('with')`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/Role/Basic.pm | 25788 bytes | Perl 角色模块主文件 |
| lib/perl5/Role/Basic/Philosophy.pod | 8601 bytes | 角色设计哲学文档 |

## 功能测试结果

### 模块自带测试 (make test)
- 304 个测试全部通过 ✅

### 扩展功能测试
- 模块加载: ✅ PASS
- 版本号验证: ✅ PASS (0.16)
- 关键字导出 (with, requires): ✅ PASS
- Role 组合 (with 多角色): ✅ PASS
- requires 约束: ✅ PASS
- 方法冲突排除 (-excludes): ✅ PASS
- 方法别名 (-alias): ✅ PASS
- 类方法覆盖 Role 方法: ✅ PASS
- Role 嵌套组合: ✅ PASS

### Conan 集成测试
- test_package smoke test 通过 ✅
- conan-verify 8 道门禁全部通过 ✅
- submit 自检通过 ✅

详细报告见: reports/test-report.md

## 注意事项

- 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名
- Conan 配方通过 `runenv_info.append_path("PERL5LIB", ...)` 设置模块搜索路径
- `with` 只能对同一包调用一次，多角色需在单次调用中传入
- 不支持 `has` 属性定义和方法修饰器（before/after/around）
- 类方法会静默覆盖 Role 提供的同名方法

---

**编译结束**: 2026-06-29 15:56
**最终状态**: published
