# perl-module-build-xsutil 0.19 适配笔记

## 编译环境
- 构建系统: perl-modulebuild (Build.PL)
- 编译日期: 2026-06-18（初次编译），2026-06-22（补丁修复）
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. 配置
perl Build.PL --install_base=$DEFAULT_PREFIX

# 2. 构建
./Build

# 3. 安装（staging）
./Build install

# 4. 测试
./Build test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ld.lld: error: unknown argument '-fstack-protector-strong' | Perl 的 ldflags/lddlflags 中包含 -fstack-protector-strong，这是编译器标志而非链接器标志，ld.lld 不识别 | 覆盖 cbuilder() 方法，从 ldflags/lddlflags 中移除该标志 |
| 2 | ExtUtils::CBuilder 检测不到编译器 | 上述 ld.lld 错误导致编译器检测失败 | 同上，cbuilder() 覆盖传递修复后的 Config |
| 3 | fatal error: 'sys/types.h' file not found | musl 头文件不在默认搜索路径 | 在 cbuilder() 中添加 -I$HOME/usr/local/include 到 ccflags |
| 4 | ld.lld: unable to find library -lc / -l:libunwind.a | 系统库不在链接器默认搜索路径 | 在 lddlflags 中添加 -L/system/lib64 -L$HOME/usr/local/lib |
| 5 | have_c_compiler() 缓存导致修复无效 | SUPER::new() 中 _set_defaults() 调用 have_c_compiler() 失败后缓存了结果 | 在 new() 中 delete $self->{properties}{_have_c_compiler} 清除缓存 |
| 6 | XS .so 从 HMDFS 加载 Permission denied | SELinux 限制：hishell_hap domain 只能加载 hnp_file 类型 | 平台限制，不影响编译产物完整性，需安装到系统目录 |

## 源码修改

补丁文件: `patches/0001-fix-ohos-linker-flags.patch`

修改文件: `lib/Module/Build/XSUtil.pm`

### 变更内容:
1. **cbuilder() 方法覆盖**: 创建 ExtUtils::CBuilder 时传入修复后的 Config 副本
   - 从 ldflags/lddlflags 移除 `-fstack-protector-strong`
   - 添加 `-L/system/lib64 -L$HOME/usr/local/lib -lunwind -lc` 到 lddlflags
   - 添加 `-I$HOME/usr/local/include` 到 ccflags（musl 头文件路径）
2. **编译器检测缓存清除**: `delete $self->{properties}{_have_c_compiler}` 确保使用修复后的 cbuilder 重新检测

## 依赖版本

- perl 5.42.0
- perl-module-build 0.4234
- ExtUtils::CBuilder 0.280242（系统自带）
- 测试依赖（已安装）:
  - File::Copy::Recursive::Reduced 0.006
  - Cwd::Guard 0.05
  - Capture::Tiny（系统自带）

## 验证结果

```bash
$ perl -MModule::Build::XSUtil -e 'print "Version: $Module::Build::XSUtil::VERSION\n"'
Version: 0.19

$ perl -MExtUtils::CBuilder -e 'my $b=ExtUtils::CBuilder->new(quiet=>1); print "have_compiler: ", $b->have_compiler?"yes":"no", "\n"'
have_compiler: yes

$ ./Build test
t/00_compile.t .. ok
t/01_build.t .... 1/2  (test 1 PASS, test 2 FAIL due to SELinux)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-build-xsutil-0.19-ohos-aarch64.tar.gz | ~20KB | 预编译包 |
| patches/0001-fix-ohos-linker-flags.patch | ~2KB | OpenHarmony 链接器修复补丁 |

## 注意事项

1. **SELinux HMDFS 限制**: XS 模块（.so 文件）从 HMDFS 路径（如 ~/usr/local/lib）加载时会被拒绝。需安装到系统目录 (/data/service/hnp) 才能正常加载。此限制与 perl-dbd-pg 相同，是平台特性。
2. **补丁条件触发**: cbuilder() 中的修复代码仅在检测到 `-fstack-protector-strong` 时触发，不影响其他平台。
3. **参考经验**: 本补丁参考 perl-dbd-pg 3.18.0 的编译经验，特别是链接器标志处理和 SELinux 限制分析。

---

**编译结束**: 2026-06-22 16:44
**最终状态**: published
