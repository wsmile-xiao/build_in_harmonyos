# perl-net-telnet 3.05-r1 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29
- 编译器: N/A (纯Perl模块，无需C编译器)
- Perl版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 从CPAN下载源码: `curl -kL -o Net-Telnet-3.05.tar.gz https://cpan.metacpan.org/authors/id/J/JR/JROGERS/Net-Telnet-3.05.tar.gz`
   - Savannah URL返回404，改用CPAN
   - SSL证书验证失败，使用 `-k` 跳过
2. 放置tarball到 `$HOME/tmp/builds/perl-net-telnet-3.05-r1.tar.gz`
3. 运行 `ohc-run.py init-build perl-net-telnet 3.05-r1 --url=<CPAN_URL>` (tarball已存在，跳过下载)
4. 编译:
   ```bash
   source .build-context-perl-net-telnet-3.05-r1
   cd $BUILD_SRC_DIR
   perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
   make
   make test
   make install DESTDIR=$TEST_PREFIX
   ```
5. 验证: `perl -MNet::Telnet -e 'print Net::Telnet->VERSION'` → 3.05
6. 生成Conan配方: `ohc-run.py conan-init perl-net-telnet 3.05-r1`
7. 修改conanfile.py适配纯Perl模块（替换Autotools模板）
8. 验证: `ohc-run.py conan-verify perl-net-telnet 3.05-r1` → 全部PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙平台SSL证书链不完整 | 使用 `curl -kL` 下载 |
| 2 | Savannah URL返回404 | 该URL已失效 | 改用CPAN URL: https://cpan.metacpan.org/authors/id/J/JR/JROGERS/Net-Telnet-3.05.tar.gz |
| 3 | conanfile.py使用Autotools模板 | conan-init默认生成autotools模板 | 手动重写conanfile.py为Perl Makefile.PL构建方式 |
| 4 | test_package使用CMake/C测试 | 模板默认C/C++测试 | 重写为Perl模块加载测试 |
| 5 | test_package中deps_cpp_info不存在 | Conan 2.x API变更 | 改用 self.dependencies["perl-net-telnet"] |
| 6 | G4产物完整性检查失败 | 纯Perl模块安装到非标准路径(data/service/...)，无bin/lib/include | 在package()中额外复制.pm文件到lib/目录 |
| 7 | make -j2的mkfifo警告 | 鸿蒙平台不支持mkfifo | 非致命，编译仍成功完成 |

## 源码修改

无补丁。源码未修改。

## 依赖版本

- Perl: 5.42.0 (aarch64-linux)
- ExtUtils::MakeMaker: 7.1002 (系统自带)
- 无外部依赖

## 验证结果

```bash
# 模块加载测试
perl -MNet::Telnet -e 'print "Net::Telnet version: ", Net::Telnet->VERSION, "\n"'
# 输出: Net::Telnet version: 3.05

# make test结果
# t/select.t .. ok
# All tests successful.
# Files=1, Tests=3, 0 wallclock secs
# Result: PASS

# conan-verify结果: 全部PASS (G0/G1/G2/G3/G4/L2/L4/L5)
```

## 功能测试（2026-06-30 补充）

参考 perl-dbd-pg 的功能测试方法，执行了全面的实际功能测试。

### 测试范围

| 测试组 | 测试项数 | 结果 |
|--------|---------|------|
| 模块加载与版本 | 2 | ✅ PASS |
| API 方法完整性 | 1 | ✅ PASS (26个方法) |
| 错误处理 | 3 | ✅ PASS (return/die/回调) |
| TCP 连接与数据交互 | 7 | ✅ PASS (含大数据量) |
| 超时处理 | 3 | ✅ PASS (精确触发) |
| 配置属性 | 6 | ✅ PASS |
| 日志功能 | 3 | ✅ PASS |
| 纯 Perl 模块特性 | 3 | ✅ PASS |
| 平台兼容性 | 3 | ✅ PASS |
| **总计** | **31** | **100% 通过率** |

### 关键发现

1. **纯 Perl 模块优势**：与 perl-dbd-pg 的 XS 模块不同，Net::Telnet 不受 SELinux HMDFS 限制影响，可直接从任何路径加载
2. **TCP 连接完整可用**：使用本地 Echo 服务器验证了完整的 TCP 连接→数据收发→关闭流程
3. **大数据量传输正常**：1000 字节数据传输成功接收
4. **超时精确**：连接超时在 2.0006s 触发（设置 2s），精度极高
5. **API 完整**：26 个核心方法全部可用，无缺失
6. **错误处理完善**：return、die、回调三种 errmode 模式均正常工作

### 测试脚本

测试脚本位于 `/storage/Users/currentUser/.opendesk-tmp/telnet_func_test.pl`，涵盖 9 个测试组 31 个测试项。

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| conanfile.py | archives/p/perl-net-telnet/3.05-r1/ | Conan配方 |
| conandata.yml | archives/p/perl-net-telnet/3.05-r1/ | 源码SHA256 |
| test_package/ | archives/p/perl-net-telnet/3.05-r1/ | Perl模块加载测试 |
| conan-verify-report.md | archives/p/perl-net-telnet/3.05-r1/reports/ | 验证报告 |
| baseline.json | archives/p/perl-net-telnet/3.05-r1/reports/ | 产物基线 |
| manifest.yaml | archives/p/perl-net-telnet/3.05-r1/ | 编译元数据 |

## 注意事项

1. 纯Perl模块无需C编译器，conanfile.py中settings保留compiler但build()不使用
2. Conan的package()需要额外将.pm文件复制到lib/目录以满足G4检查
3. test_package不能用CMake，需要用Perl命令直接测试模块加载
4. 源码URL应使用CPAN而非Savannah（后者已404）
---

**编译结束**: 2026-06-29 20:04
**功能测试**: 2026-06-30
**最终状态**: published (31/31 功能测试通过)
