# perl-net-async-irc 0.12-r0 适配笔记

## 编译环境
- 构建系统: Perl Module::Build (Build.PL)
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published (conan-verify 全通过)

## 编译步骤

### Step 1: init-build (自动)
通过 `ohc-run.py init-build perl-net-async-irc 0.12-r0` 初始化，下载源码、创建归档骨架。

### Step 2: AI 编译
Net::Async::IRC 是纯 Perl 模块，使用 Module::Build 构建系统：

```bash
# 配置
perl Build.PL --install_base=$PACKAGE_FOLDER/perl5

# 构建
./Build

# 安装 (staging)
./Build install
```

无需 configure/make，直接使用 Perl 的 Module::Build。

### Step 2.5: Conan 配方生成与验证
```bash
python3 ohc-run.py conan-init perl-net-async-irc 0.12-r0
python3 ohc-run.py conan-verify perl-net-async-irc 0.12-r0
```

conan-verify 8 道门禁全部通过 (G0-G4 + L2/L4/L5)。

### Step 3: finish (自动收尾)
归档关闭、conan-verify、知识完整性检查、摘要生成。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G4 初始失败 | 首次运行时 Conan 缓存未建立，产物路径未找到 | 重新运行 conan-verify 后 G4 PASS（包缓存已建立） |
| 2 | PERL5LIB 覆盖系统 site_perl | Perl 的 PERL5LIB 会替换 site_perl 编译时路径，导致 IO::Async 等系统模块找不到 | 测试时使用 `-I` 参数而非 PERL5LIB 环境变量 |
| 3 | Future::AsyncAwait XS 依赖缺失 | CPAN 依赖未预装 | 手动下载并编译 Future::AsyncAwait 0.47 + XS::Parse::Sublike 0.10 |
| 4 | musl C 库头文件不完整 | musl 安装时缺少 68 个标准头文件（wchar.h, stdio.h 等） | 从 musl 1.2.5 源码复制缺失头文件到 ~/usr/local/include/ |
| 5 | -fstack-protector-strong 不支持 | Perl Config 中的 ccflags 包含此参数，clang/ld.lld 不支持 | 编译时手动指定 ccflags，不使用 Perl Config 默认值 |
| 6 | 链接缺少 libc/libunwind | OpenHarmony 缺少 CRT 文件 | 使用 `-nostartfiles -L~/usr/local/lib -lc` 链接参数 |
| 7 | newPADxVOP 宏冲突 | Perl 5.42 的 embed.h 定义了 3 参数宏，Future::AsyncAwait 定义 4 参数函数 | 在 hax/perl-additions.c.inc 添加 `#undef newPADxVOP` |
| 8 | XS .so 无法加载 | SELinux HMDFS 限制，hishell_hap 只能加载 hnp_file 类型 | 平台限制，需管理员安装到 /data/service/hnp/ |

## 源码修改

### Future::AsyncAwait 0.47 — hax/perl-additions.c.inc
```c
// 在第 43 行前添加：
#ifdef newPADxVOP
#undef newPADxVOP
#endif
```
原因：Perl 5.42 的 embed.h 定义了 `newPADxVOP(a,b,c)` 宏（3 参数），与 Future::AsyncAwait 的 4 参数静态函数冲突。

### musl 头文件补全
从 musl 1.2.5 源码 (`~/tmp/builds/musl-1.2.5.orig/include/`) 复制 68 个缺失标准头文件到 `~/usr/local/include/`，包括：wchar.h, stdio.h, stdlib.h, string.h, math.h, ctype.h, endian.h 等。

## 依赖版本

| 依赖 | 版本 | 类型 | 状态 |
|------|------|------|------|
| Perl | 5.42.0 | 运行时 | ✅ 系统预装 |
| IO::Async | 0.805 | 纯 Perl | ✅ 系统预装 |
| Protocol::IRC | 0.13 | 纯 Perl | ✅ 系统预装 |
| Future | 0.52 | 纯 Perl | ✅ 系统预装 |
| Future::Utils | 0.52 | 纯 Perl | ✅ 系统预装 |
| Future::AsyncAwait | 0.47 | XS | ✅ 已编译，⚠️ 需管理员安装 |
| XS::Parse::Sublike | 0.10 | XS | ✅ 已编译，⚠️ 需管理员安装 |

## 验证结果

```bash
# Conan 验证
$ python3 ohc-run.py conan-verify perl-net-async-irc 0.12-r0
→ G0-G4+L2/L4/L5 全 PASS，可标记 published

# Protocol::IRC::Message 解析
$ perl -MProtocol::IRC::Message -e '...'
→ Prefix: irc.example.com, Command: PRIVMSG, Args: #channel | Hello, world!

# 模块语法检查
$ perl -c Net/Async/IRC/Protocol.pm
→ syntax OK

# XS 模块加载
$ perl -MFuture::AsyncAwait -e '...'
→ Permission denied (SELinux HMDFS 限制)
```

## 注意事项

1. **PERL5LIB 问题**: conanfile.py 的 `package_info()` 使用 `env_info.PERL5LIB`，会覆盖系统 site_perl 路径。消费者使用此包时需注意同时包含系统 Perl 库路径。建议后续改为 `cpp_info.includedirs` 或自定义 env 变量。

2. **XS 依赖未打包**: Future::AsyncAwait 和 XS::Parse::Sublike 尚未打包为 Conan 配方。conanfile.py 的 `requirements()` 中以注释形式标注，待依赖打包后启用。

3. **SELinux 限制**: 与 perl-dbd-pg 相同的平台限制。XS 模块（.so 文件）无法从 HMDFS 目录加载，需安装到 `/data/service/hnp/` 系统目录。Net::Async::IRC 本身是纯 Perl，一旦 XS 依赖安装即可完整使用。

4. **musl 头文件**: 编译 XS 模块时需要完整的 musl C 库头文件。当前系统安装的 musl 缺少 68 个标准头文件，已从源码补全。后续编译其他 XS 模块时可能也需要检查头文件完整性。

---

**编译结束**: 2026-06-25 18:10
**最终状态**: published (conan-verify 全通过)
