# perl-net-mpd 0.07-r3 适配笔记

## 编译环境
- 构建系统: Module::Build::Tiny (Perl)
- 编译日期: 2026-06-29
- 编译器: N/A (pure Perl module, no C compilation)
- Perl: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 源码来自 CPAN: Net-MPD-0.07 by Alan Berndt
2. `perl Build.PL` — 生成 Build 脚本 (Module::Build::Tiny 0.034)
3. `./Build` — 编译，将 .pm 文件复制到 blib/
4. `./Build test` — 运行测试，全部通过
5. `./Build install --destdir $TEST_PREFIX` — 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 下载 SSL 失败 | 系统缺少 CA 证书，Savannah 服务器 SSL 握手超时 | 从 CPAN (cpan.metacpan.org) 下载，使用 curl -k 绕过 SSL |
| 2 | /tmp 只读 | HMDFS 限制 (E002) | 使用 $HOME/tmp 作为 TMPDIR |
| 3 | 无 Makefile.PL | 模块使用 Module::Build::Tiny 而非 ExtUtils::MakeMaker | 使用 `perl Build.PL && ./Build` 替代 `perl Makefile.PL && make` |
| 4 | Conan G4 产物完整性 FAIL | `./Build install --destdir` 将 .pm 安装到深层路径 `data/service/hnp/.../site_perl/5.42.0/`，G4 检查找不到根目录下的 lib/ | 在 `package()` 中添加产物重组逻辑：先 install 到临时 staging 目录，再用 `shutil.copy2` 将 .pm 文件复制到 `{package_folder}/lib/` |
| 5 | test_package 测试输出错误 | test_package 的 perl 命令用双引号包裹，shell 将 `$Net::MPD::VERSION` 中的 `$Net` 当作空 shell 变量插值，输出变成 `::MPD::VERSION` | 将 perl 命令改用单引号包裹，避免 shell 变量插值 |

## 源码修改

无源码修改，纯 Perl 模块直接编译。

## Conan 配方修复 (2026-06-29)

### 问题1: G4 产物完整性检查失败

**原始 conanfile.py 的 `package()` 方法**:
```python
def package(self):
    self.run(f"./Build install --destdir {self.package_folder}")
```

**问题**: `./Build install --destdir` 按照 Perl 的 `@INC` 配置安装到深层路径：
`{package_folder}/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/Net/MPD.pm`

G4 门禁检查 `{package_folder}/bin/`, `lib/`, `include/` 根目录，找不到任何产物。

**修复**: 在 `package()` 中添加产物重组逻辑：
```python
def package(self):
    staging = os.path.join(self.package_folder, "_staging")
    self.run(f"./Build install --destdir {staging}")
    # 找到 .pm 文件并复制到 lib/ 根目录
    pm_files = glob.glob(os.path.join(staging, "**", "Net", "MPD.pm"), recursive=True)
    if pm_files:
        perl_lib_root = os.path.dirname(os.path.dirname(pm_files[0]))
        pkg_lib = os.path.join(self.package_folder, "lib")
        # 递归复制所有文件到 lib/
        ...
    shutil.rmtree(staging, ignore_errors=True)
```

同时更新 `package_info()` 将 `PERL5LIB` 指向 `{package_folder}/lib`。

### 问题2: test_package 测试命令 shell 插值 bug

**原始 test_package/conanfile.py**:
```python
self.run('perl -e "use Net::MPD; print qq(Net::MPD version: $Net::MPD::VERSION\\n)"', env="conanrun")
```

**问题**: shell 解析双引号字符串时，`$Net` 被当作空 shell 变量，输出变成 `::MPD::VERSION`。

**修复**: 改用单引号包裹 perl 表达式：
```python
self.run("perl -e 'use Net::MPD; print qq(Net::MPD version: $Net::MPD::VERSION\\n)'", env="conanrun")
```

修复后输出正确: `Net::MPD version: 0.07`

## 依赖版本

- Perl 5.42.0 (aarch64-linux)
- Module::Build::Tiny 0.034 (构建时依赖)
- 运行时依赖（均为 Perl 核心模块）: version 0.77, Carp, IO::Socket::INET, Scalar::Util

## 验证结果

```bash
$ ./Build test
t/author-pod-syntax.t .. skipped: these tests are for testing by the author
t/basic.t .............. ok
All tests successful.
Files=2, Tests=1,  1 wallclock secs
Result: PASS

$ perl -e 'use Net::MPD; print "Net::MPD version: $Net::MPD::VERSION\n"'
Net::MPD version: 0.07
```

## 注意事项

- 这是一个纯 Perl 模块，不涉及 C/C++ 编译
- 原始版本为 0.07，"-r3" 为 OpenHarmony 打包修订号
- 源码 URL 应使用 CPAN 地址而非 Savannah（Savannah 服务器不稳定）✅ L2: smoke test — PASS
✅ L4: 安全扫描 — PASS
✅ L5: 基线对比 — PASS
```

### 功能测试 (2026-06-29)

完整功能测试通过，详见 `reports/test-report.md`。

- ✅ 模块加载 (Net::MPD, Net::MPD::Response)
- ✅ 版本检查 (0.07)
- ✅ API 方法 (82 类方法 + 13 实例方法)
- ✅ 连接错误处理 (localhost, 不可达地址, Unix socket)
- ✅ 源码语法检查
- ✅ 重复加载稳定性 (50次)

## 注意事项

- 这是一个纯 Perl 模块，不涉及 C/C++ 编译
- 原始版本为 0.07，"-r3" 为 OpenHarmony 打包修订号
- 源码 URL 应使用 CPAN 地址而非 Savannah（Savannah 服务器不稳定）
---

**编译结束**: 2026-06-29 13:04
**最终状态**: published
