# perl-net-jabber-bot 2.1.7-r0 适配笔记

## 编译环境
- 构建系统: custom (perl Makefile.PL / ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (无需 C 编译，纯 Perl 模块)
- 状态: published

## 编译步骤

```bash
# 1. 源码下载和解压（由 conan source() 自动完成）
# 2. 构建（纯 Perl 模块，无 C 编译步骤）
perl Makefile.PL
make
# 3. 安装到 staging 目录
make install DESTDIR=$PACKAGE_FOLDER
```

Net::Jabber::Bot 是一个纯 Perl 模块，`make` 仅执行 `cp lib/Net/Jabber/Bot.pm blib/lib/Net/Jabber/Bot.pm`，
无 C 编译步骤。`make install` 将 .pm 文件安装到 Perl 的 site_perl 目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4 产物完整性检查失败 | `conan cache path <ref>` 返回 recipe 导出文件夹而非二进制包文件夹 | 修复 conan_verify.py: G2 提取 pkg_id，G4 使用 `ref:pkg_id` 获取正确路径 |
| 2 | Conan 缓存陈旧引用 | `conan remove -c` 未完全清除二进制包索引 | 使用 `--build="perl-net-jabber-bot/*"` 强制重建 |
| 3 | profile 中 `os.cpu.arch` 无效 | Conan 2.12 不支持 `os.cpu` 子设置 | 修正为 `arch=armv8` |
| 4 | XML::Stream::Parser 警告 | 代码中 `!` 和 `==` 优先级问题 | 非致命警告，不影响功能 |

## 源码修改

无源码修改。纯 Perl 模块在鸿蒙平台上开箱即用。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| perl | 5.42.0 | 系统预装 (HNP) |
| Net::Jabber | 2.0 | 用户已安装 |
| Moose | 2.4000 | 用户已安装 |
| XML::Stream | 1.24 | 用户已安装 |
| Digest::SHA | 6.04 | 系统模块 |
| LWP::UserAgent | 6.81 | 用户已安装 |
| HTTP::Request | 6.46 | 用户已安装 |
| Parallel::ForkManager | 未安装 | 可选依赖 (StartParallel 模式) |

## 验证结果

```bash
# conan-verify 全部门禁通过
G0: ✅ PASS  预构建风险评估
G1: ✅ PASS  配方完整性
G2: ✅ PASS  conan create 成功
G3: ✅ PASS  静态链接验证 (纯库包跳过)
G4: ✅ PASS  产物完整性 (lib/: 1 .pm, 3 其他)
L2: ✅ PASS  smoke test (纯库包跳过)
L4: ✅ PASS  安全扫描 (无 ELF 文件)
L5: ✅ PASS  产物基线对比

# 功能测试
$ perl -MNet::Jabber::Bot -e 'print "Net::Jabber::Bot loaded OK\n"'
Net::Jabber::Bot loaded OK

$ perl -MNet::Jabber::Bot -e 'print "Version: $Net::Jabber::Bot::VERSION\n"'
Version: 2.1.7
```

## 注意事项

1. **纯 Perl 模块**: 无 C/XS 编译，不受 SELinux HMDFS 限制，可从任意路径加载
2. **XML::Stream 警告**: `Possible precedence problem between ! and numeric eq` 是非致命警告，不影响功能
3. **Parallel::ForkManager**: StartParallel 模式需要此模块，未安装时仅影响后台并行处理功能
4. **Jabber 服务器**: Bot 对象创建时会尝试连接 Jabber 服务器，无服务器时连接失败是正常行为
5. **conan_verify.py 修复**: G4 检查中 `conan cache path` 现在使用 `ref:pkg_id` 获取二进制包文件夹
---

**编译结束**: 2026-06-26 19:27
**最终状态**: published
