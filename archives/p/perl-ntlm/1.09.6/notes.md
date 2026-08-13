# perl-ntlm 1.09.6 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (perl Makefile.PL + make)
- 编译日期: 2026-06-29 (初次), 2026-07-01 (修复完善)
- 编译器: 不需要（纯 Perl 模块）
- 状态: built

## 编译步骤

1. 下载源码: curl -kL 下载 NTLM-1.09.tar.gz (CPAN 模块 Authen::NTLM)
2. 解压源码到构建目录
3. 设置环境: PERL_CANARY_STABILITY_NOPROMPT=1
4. 生成 Makefile: perl Makefile.PL
5. 编译: make
6. 测试: make test (34 tests, all passed)
7. 安装: make install DESTDIR=$TEST_PREFIX
8. 验证: perl -I<libpath> -MAuthen::NTLM -e 'print $Authen::NTLM::VERSION'

## 遇到的问题与解决方案

### 初次编译 (2026-06-29)

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | curl 下载源码时 SSL CERTIFICATE_VERIFY_FAILED | 使用 curl -kL 绕过证书验证 |
| 2 | /tmp 只读 | 鸿蒙平台 /tmp 目录只读 | 使用 $HOME 和 $TMPDIR |
| 3 | 搜索URL不准确 | search-url 返回的 savannah URL 404 | 通过 MetaCPAN API 查找正确 CPAN URL |
| 4 | conan create package() 失败 | os.path.join 绝对路径覆盖问题 | 改用 blib 目录直接 copy |
| 5 | test_package deps_cpp_info 失败 | Conan 2 API 变更 | 改用 self.dependencies[name].package_folder |

### 修复完善 (2026-07-01)

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 6 | test_package 输出错误 | Perl -e 命令使用 shell 双引号，`$Authen::NTLM::VERSION` 被 shell 展开为空 | 改用 shell 单引号 + 字符串拼接，避免 shell 变量展开和 Python f-string 花括号冲突 |
| 7 | 缺少软件级 manifest.yaml | 原始编译未生成软件级文件 | 新建，含版本索引和 OHOS 适配知识 |
| 8 | 缺少软件级 README.md | 原始编译未生成 | 新建，含功能概述和 OHOS 适配说明 |
| 9 | 版本级 manifest 缺少 conan_ref | 字段缺失 | 添加 conan_ref: perl-ntlm/1.09.6@ohpcd/stable |
| 10 | 缺少 test_package/MANIFEST.yml | CI L0e 门禁要求 | 新建，含上游测试声明 (5 个测试文件) |
| 11 | build.system 值不正确 | 原值为 "custom" | 修正为 "perl" |

## test_package 引号转义问题详解

**原始代码** (有 bug):
```python
self.run(f'perl -I{perl_lib} -MAuthen::NTLM -e "print \'Authen::NTLM version: \', $Authen::NTLM::VERSION, \\"\\n\\"; 1"')
```

**问题**: shell 双引号内 `$Authen::NTLM::VERSION` 被展开为空，输出 `::NTLM::VERSIONn`

**修复代码**:
```python
self.run("perl -I" + perl_lib + " -MAuthen::NTLM -e 'print \"Authen::NTLM version: \", $Authen::NTLM::VERSION, chr(10)'")
```

**修复要点**:
1. 使用 shell 单引号包裹 -e 参数，防止 shell 展开 `$` 变量
2. 使用字符串拼接替代 f-string，避免 Perl `qq{}` 花括号被 Python f-string 误解析
3. 使用 `chr(10)` 替代 `\n`，避免多层转义问题

## 源码修改

无补丁，纯 Perl 模块无需修改源码。

## 依赖版本

- Perl 5.42.0 (系统自带, aarch64-linux)
- MIME::Base64 (Perl 核心模块)
- Digest::HMAC_MD5 (Perl 核心模块)

## 验证结果

### make test 结果
```
t/01_load.t .. ok
t/02_ntlm.t .. ok
t/03_oo.t .... ok
t/04_v2.t .... ok
t/99_pod.t ... skipped: Test::Pod 1.00 required for testing POD
All tests successful.
Files=5, Tests=34, 1 wallclock secs
Result: PASS
```

### 功能测试结果 (27 个断言)
- 模块加载与版本: 2/2 PASS
- 子模块加载 (DES, MD4): 2/2 PASS
- Base64 编解码: 2/2 PASS
- MD4 哈希: 1/1 PASS
- DES 加密: 2/2 PASS
- LM/NTLM 密码哈希: 2/2 PASS
- NTLMv1 认证流程: 3/3 PASS
- NTLMv2 认证流程: 3/3 PASS
- LMv2/NTv2 响应: 2/2 PASS
- OO 接口: 4/4 PASS
- Unicode 转换: 2/2 PASS
- 常量检查: 2/2 PASS

### Conan 验证结果
- G0-G4 + L2/L4/L5: 全部 PASS
- conan create: 成功
- test_package: 输出 `Authen::NTLM version: 1.09`

### 平台信息
- OS: HarmonyOS (HongMeng Kernel 1.12.0, aarch64)
- Perl: 5.42.0 (aarch64-linux)
- SELinux: 无限制（纯 Perl 模块无 .so 文件）

## 交付物

| 文件 | 说明 |
|------|------|
| lib/perl5/Authen/NTLM.pm | 主模块 (12KB) |
| lib/perl5/Authen/NTLM/DES.pm | DES 子模块 (7KB) |
| lib/perl5/Authen/NTLM/MD4.pm | MD4 子模块 (5KB) |

## 归档文件清单

### 软件级
- manifest.yaml — 软件元数据 + 版本索引
- README.md — 软件描述 + OHOS 适配

### 版本级
- conanfile.py — Conan 2.x 配方 (CI 唯一输入)
- conandata.yml — 源码 URL + SHA256
- manifest.yaml — 版本编译元数据
- notes.md — 适配笔记 (本文件)
- test_package/conanfile.py — Conan L1 测试
- test_package/MANIFEST.yml — 上游测试声明
- reports/test-report.md — 功能测试报告
- reports/quality-report.md — 质量报告
- reports/reviewer-report.md — 上库评估报告
- reports/conan-verify-report.md — Conan 验证报告
- reports/conan-create.log — Conan 构建日志
- reports/baseline.json — 产物基线

## 注意事项

- 这是纯 Perl 模块，无需 C 编译器
- conanfile.py 使用 blib 目录进行打包，而非 make install DESTDIR 方式
- test_package 使用 VirtualRunEnv 生成器而非 CMake
- test_package 的 Perl -e 命令必须使用 shell 单引号防止变量展开
- 纯 Perl 模块不受 SELinux HMDFS 限制，与 XS 模块 (如 perl-dbd-pg) 不同

---

**编译结束**: 2026-06-29 20:01 (初次)
**修复完善**: 2026-07-01 15:55
**最终状态**: built
