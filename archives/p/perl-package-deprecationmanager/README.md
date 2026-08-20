# perl-package-deprecationmanager

Manage deprecation warnings for your Perl distribution (Package::DeprecationManager CPAN module).

## 软件信息

- **官网**: https://metacpan.org/dist/Package-DeprecationManager
- **源码**: https://github.com/moose/Package-DeprecationManager
- **许可证**: Artistic-2.0 (GPL Compatible)
- **分类**: perl-module
- **模块类型**: 纯 Perl 模块（无 XS/C 编译组件）

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.18-r1 | built | 2026-07-02 | 纯 Perl 模块，conan-verify 全部通过 |

## 运行依赖

- perl (5.42.0+)
- Package::Stash 0.40 (vendored)
- Params::Util 1.102 (vendored)
- Module::Implementation 0.09 (vendored)
- Module::Runtime 0.016 (vendored)
- Try::Tiny 0.31 (vendored)
- Sub::Install 0.928 (vendored)
- Sub::Util (系统 Perl)
- List::Util (系统 Perl)
- Carp (系统 Perl 核心模块)

## 使用说明

Package::DeprecationManager 用于在 Perl 模块中管理弃用警告。它会在导入时向调用者包安装 `import()` 和 `deprecated()` 两个子例程。

### 基本用法

```perl
package My::Module;

use Package::DeprecationManager -deprecations => {
    'My::Module::old_method' => '0.02',
    'feature_x'              => '0.05',
};

sub old_method {
    deprecated();           # 生成默认警告
    deprecated('custom message');  # 自定义消息
    deprecated(
        message => 'Feature X is deprecated',
        feature => 'feature_x',
    );
}
```

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-package-deprecationmanager/0.18-r1
```

安装后通过 `PERL5LIB` 环境变量加载模块。

### 注意事项

1. 纯 Perl 模块，无 SELinux/ELF 签名等平台限制
2. conanfile.py 使用 `self.run()` 调用 `perl Makefile.PL`，不使用 CMake
3. `package_info()` 使用 `runenv_info.append_path("PERL5LIB", ...)` 而非 `cpp_info.libs`
4. settings 包含 `os`, `compiler`, `build_type`, `arch` 四项（CI L0p 门禁要求）

---
*OpenHarmony 编译归档 · 2026-07-02*
mony 编译归档 · 2026-07-02*
