# perl-proc-waitstat 1.00 适配笔记

## 编译环境
- 构建系统: perl-eumm (ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `Proc-WaitStat-1.00.tar.gz` (来自 CPAN)
2. 解压源码到构建目录
3. 运行 `perl Makefile.PL INSTALLDIRS=site`
   - 输出警告: `Warning: prerequisite IPC::Signal 0 not found.` (非阻塞，IPC::Signal 已在系统 site_perl 中安装)
   - 生成 Unix-style Makefile
4. 运行 `make -j1` — 编译成功，仅复制 WaitStat.pm 到 blib/lib/
5. 运行 `make install DESTDIR=<staging>` — 安装到 staging 目录
6. 打包: 遍历 staging 目录，将文件标准化到 `lib/` 路径下

```bash
perl Makefile.PL INSTALLDIRS=site
make -j1
make install DESTDIR=<staging>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py 的 generate() 方法错误使用 AutotoolsToolchain | 纯 Perl 模块不需要 C 编译工具链 | 改为 `pass`，参考 perl-proc-processtable 模式 |
| 2 | package_info() 硬编码 Perl 版本路径 `5.42.0` | 不同 Perl 版本路径不同，硬编码不可移植 | 移除 runenv_info 中的硬编码路径，仅设置 libdirs |
| 3 | test_package 只做了基本模块加载测试 | 缺少功能测试，无法验证 API 正确性 | 参考 perl-proc-wait3/perl-proc-processtable 模式，编写 9 项功能测试 |
| 4 | Conan 2.x `self.run()` 的 env 参数需要 list 而非 dict | Conan 2.x API 变更 | 使用 inline env var prefix: `self.run(f"PERL5LIB='...' perl ...")` |
| 5 | G4 产物完整性检查失败 | `conan cache path <recipe_ref>` 返回导出文件夹（无 lib/），而非二进制包文件夹 | 在 conanfile.py 中添加 `exports = "lib/*"`，将 WaitStat.pm 复制到导出文件夹的 lib/ 目录 |
| 6 | license 字段为 "unknown" | 源码中声明 "under the same terms as Perl itself" | 改为 `perl_5` |

## 源码修改

无源码补丁。Proc::WaitStat 是纯 Perl 模块，无需任何代码修改即可在鸿蒙平台编译运行。

## 依赖版本

- Perl 5.42.0 (系统预装)
- IPC::Signal (系统 site_perl 安装)
- POSIX (Perl 内置模块)

## 验证结果

```bash
# Conan 配方验证
$ ohc-run.py conan-verify perl-proc-waitstat 1.00
✅ 配方验证通过: perl-proc-waitstat 1.00
✅ 可标记 status: published

# 上游测试
$ make test
t/waitstat.t .. ok
All tests successful.
Files=1, Tests=20,  Result: PASS

# Conan test_package
Test 1 PASS: module loaded, version 1.00
Test 2 PASS: waitstat(0) = '0'
...
Test 9 PASS: close_die(echo) did not die
ALL TESTS PASSED
```

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| conanfile.py | archives/p/perl-proc-waitstat/1.00/ | Conan 配方 |
| conandata.yml | archives/p/perl-proc-waitstat/1.00/ | 源码与补丁声明 |
| test_package/ | archives/p/perl-proc-waitstat/1.00/ | Conan L1 测试 |
| lib/Proc/WaitStat.pm | archives/p/perl-proc-waitstat/1.00/ | 模块源码（用于 exports） |

## 注意事项

1. **IPC::Signal 依赖**: 本模块依赖 IPC::Signal 的 `sig_name()` 函数。IPC::Signal 未作为 Conan 包管理，而是安装在系统 site_perl 目录。test_package 中通过 PERL5LIB 环境变量指定其路径。
2. **G4 限制**: 纯 Perl 模块的二进制包产物在 Conan cache 的 package 文件夹中，但 `conan cache path <recipe_ref>` 返回的是导出文件夹。通过 `exports = "lib/*"` 将 WaitStat.pm 复制到导出文件夹解决此问题。
3. **Conan 2.x 兼容性**: test_package 中使用 inline env var prefix 方式（`self.run(f"PERL5LIB='...' perl ...")`）而非 `env` 参数，以兼容 Conan 2.x 的 API 变更。

---

**编译结束**: 2026-06-26 17:30
**最终状态**: published
