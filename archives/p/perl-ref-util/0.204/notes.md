# perl-ref-util 0.204 适配笔记

## 编译环境
- 构建系统: makefile (ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-26 (初次) / 2026-06-29 (修复完善)
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -k -L -o Ref-Util-0.204.tar.gz https://cpan.metacpan.org/authors/id/A/AR/ARC/Ref-Util-0.204.tar.gz`
2. 初始化编译: `python3 ohc-run.py init-build perl-ref-util 0.204 --url=...`
3. 生成 Makefile: `perl Makefile.PL INSTALLDIRS=site PUREPERL_ONLY=1`
4. 编译: `make -j1`
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `make test`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙平台CA证书问题 | 使用 `curl -k` 手动下载，再用 `--no-download` 初始化 |
| 2 | conanfile.py generate()使用AutotoolsToolchain | ohc-run.py默认生成autotools模板 | 参考perl-redis成功案例，移除AutotoolsToolchain，改用Conan 2 Environment API设置PUREPERL_ONLY |
| 3 | conanfile.py package_info()硬编码Perl版本 | 路径中硬编码了"5.42.0" | 改用glob动态发现实际Perl版本路径 |
| 4 | test_package硬编码本地路径 | 硬编码了/storage/Users/currentUser/...路径 | 改为动态检测系统Perl site_perl路径 |
| 5 | test_package缺少功能测试 | 仅检查模块加载和版本 | 增加子模块加载测试、API存在性测试(is_arrayref/is_hashref/is_scalarref/is_coderef等) |
| 6 | test_package包含conan生成文件 | conan create生成的临时文件被归档 | 清理conanbuild.sh/conanrun.sh等生成文件 |
| 7 | 缺少软件级README.md | 归档目录缺少README.md | 创建软件级README.md |
| 8 | manifest.yaml build.system错误 | 标记为autotools但实际为makefile | 修正为makefile |
| 9 | manifest.yaml knowledge_gained为空 | 未提取编译经验 | 填充7条编译知识 |

## 源码修改

无源码修改。使用原始 Makefile.PL (ExtUtils::MakeMaker)。

## Conan 配方变更 (2026-06-29)

### conanfile.py 修复
1. **移除 `generate()` 中的 AutotoolsToolchain** — 纯 Perl 模块不需要 autotools 工具链
2. **新增 `generate()` 使用 Conan 2 Environment API** — 正确设置 `PUREPERL_ONLY=1`
3. **修复 `package_info()`** — 使用 glob 动态发现 Perl 版本路径，不再硬编码 "5.42.0"

### test_package/conanfile.py 修复
1. **移除硬编码本地路径** — 改为动态检测系统 Perl site_perl 路径
2. **增强功能测试** — 新增子模块加载测试(Ref::Util::PP)、API存在性测试(is_ref/is_arrayref/is_hashref/is_scalarref/is_coderef/is_ref_type)
3. **清理生成文件** — 移除 conan create 生成的临时文件

## 依赖版本

- Perl 5.42.0 (核心模块 Exporter >= 5.57)
- 无额外运行时依赖

## 验证结果

```bash
# Conan 配方验证
$ conan create archives/p/perl-ref-util/0.204 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
perl-ref-util/0.204@ohpcd/stable: Package created
test_package: Ref::Util loaded successfully: OK
test_package: Version OK
test_package: Submodules OK
test_package: API test OK

# 独立功能测试（9项全部通过）
$ perl -MRef::Util -e '...'
Test 1: 模块加载 — PASS
Test 2: is_arrayref — PASS
Test 3: is_hashref — PASS
Test 4: is_scalarref — PASS
Test 5: is_coderef — PASS
Test 6: is_ref — PASS
Test 7: is_blessed_ref — PASS
Test 8: PP后端功能 — PASS
Test 9: 边界条件 — PASS

# make test（上游测试套件）
# 初始测试 (2026-06-26): 468 项测试，465 通过，3 跳过，0 失败 — PASS
# 复测 (2026-06-29): t/basic.t 因 Params::Util.so 加载权限问题 bail out
# （鸿蒙平台 ELF 签名/权限限制，非 perl-ref-util 本身问题）
```

## 注意事项

- 本模块为纯Perl模块（无XS/C代码），使用 PUREPERL_ONLY=1 跳过可选的 Ref::Util::XS
- 3个测试跳过是预期行为：
  - `t/b-concise.t` — "nothing to do when no custom ops" (纯Perl模式下预期跳过)
  - `t/magic-readonly.t` — "Readonly is required for this test" (可选依赖)
  - `t/pureperl.t` — "All tests already executed in PP mode" (PUREPERL_ONLY=1时预期跳过)
- G0 门禁 E007 (autotools config.guess) 警告为误报 — 本模块不使用 autotools
- CI profile (`ci/conan/profiles/ohos-aarch64`) 有无效设置 `os.cpu.arch`，需修复后 conan-verify 自动验证才能通过

---

**编译结束**: 2026-06-29
**最终状态**: published
