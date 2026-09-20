# kstart 4.3 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.71 + automake 1.16, rra-c-util 宏集)
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (OHOS aarch64, musl)
- 状态: published

## 编译步骤

```
conan create archives/k/kstart/4.3 --profile:build ci/conan/profiles/ohos-aarch64 \
  --profile:host ci/conan/profiles/ohos-aarch64
```

recipe 内部流程（conanfile.py build()）:
1. `get()` 下载 kstart-4.3.tar.gz（sha256 校验）后 `apply_conandata_patches()` 依序应用 5 个补丁
2. `./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
     --with-krb5-include=$CONAN_KRB5/include --with-krb5-lib=$CONAN_KRB5/lib \
     LDFLAGS="-L$CONAN_KRB5/lib -Wl,-rpath,$CONAN_KRB5/lib"`
3. `make -j1`（HMDFS jobserver fifo EPERM 规避）
4. `make check -j1`（真实上游测试套件，tests/runtests over tests/TESTS）
5. `make install` → package_folder；OHOS 下对 bin/k5start、bin/krenew 做 binary-sign-tool 自签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段目录权限 077 导致 HMDFS 打包异常 | configure 脚本起始处 umask 077 | 0001 补丁将 configure 中 umask 改为 022，recipe 中构建全程 os.umask(0o022) 双保险 |
| 2 | config.guess 无法识别 OHOS | 上游 config.guess 无 ohos 分支 | 0002 补丁增加 aarch64-unknown-linux-ohos 识别 |
| 3 | config.sub 拒绝 ohos 三元组 | 上游 config.sub 无 linux-ohos | 0003 补丁放行 linux-ohos |
| 4 | make check 时 kafs 测试编译失败 | tests/kafs 的 Makefile 缺 KRB5_CPPFLAGS，交叉环境下头文件路径丢失 | 0004 补丁在 Makefile.am + Makefile.in 中为 tests_kafs_basic_CPPFLAGS / tests_kafs_haspag_t_CPPFLAGS 补上 $(KRB5_CPPFLAGS) $(KAFS_CPPFLAGS) |
| 5 | 测试脚本无法执行 | 20 个 Perl 测试/辅助脚本 shebang 硬编码 /usr/bin/perl，OHOS 无此路径 | 0005 补丁改为 /usr/bin/env perl，原 -w 脚本追加 use warnings 保持语义 |
| 6 | make 并行构建随机失败 | HMDFS 上 automake jobserver fifo EPERM (E074) | make 统一 -j1 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| 0001-configure-umask-022.patch | configure 起始 umask 077 → 022 |
| 0002-config-guess-ohos.patch | config.guess 识别 aarch64-unknown-linux-ohos |
| 0003-config-sub-ohos.patch | config.sub 放行 linux-ohos 三元组 |
| 0004-fix-kafs-tests-krb5-cppflags.patch | tests/kafs Makefile.am/Makefile.in 增加 KRB5_CPPFLAGS |
| 0005-port-perl-test-shebangs.patch | 20 个 Perl 脚本 shebang → /usr/bin/env perl |

## 依赖版本

- krb5/1.22.1（仓库 Conan 包，--with-krb5-include/--with-krb5-lib 直接指向包内 include/lib）
- perl（测试期依赖，PATH 可解析即可，由 0005 保证）

## 验证结果

```bash
# conan create 最终结果
...  (见 reports/ 下完整日志)

# 上游 make check（build() 内执行，test-suite.log 汇总）
All tests successful, 20 tests skipped.
Files=29, Tests=187
# HMBS_UPSTREAM_TEST_RESULT: discovered=29 executed=187 passed=187 skipped=20

# test_package 冒烟（SMOKE_SUMMARY 输出）
#   CLI 契约: k5start/krenew -h → Usage, rc=0；裸调用 rc=1
#   OHOS 专项: AArch64 ELF64 / musl interpreter / RUNPATH→Conan krb5 lib /
#              .codesign 段存在 / 无 /usr/lib 泄漏
```

## 交付物

| 文件 | 说明 |
|------|------|
| package/bin/k5start | 已签名 OHOS aarch64 ELF |
| package/bin/krenew | 已签名 OHOS aarch64 ELF |
| package/share/man/man1/k5start.1, krenew.1 | man pages |
| package/licenses/LICENSE | MIT 许可证 |

## 注意事项

- kstart 是纯应用包（无库产物）：`cpp_info.libdirs=[]`, `includedirs=[]`，消费者只使用 bin/k5start 与 bin/krenew
- usage() 语义：`-h` 退出 0、裸调用退出 1、**无** `--version` 长选项——冒烟测试按此契约编写，避免误用长选项导致挂起/误判
- 上游 20 个 SKIP 为条件跳过（无 keytab、无 krb5.conf、AFS、fakeroot、author-only、docs），属上游自身行为，保留为 SKIP，不计失败
- R36: krb5/1.22.1 为仓库已发布依赖，无未发布依赖阻塞
