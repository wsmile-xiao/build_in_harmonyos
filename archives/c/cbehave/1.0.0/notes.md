# cbehave 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-30
- 编译器: clang 15.0.4 / clang++ / llvm-ar / llvm-ranlib
- 状态: built

## 编译步骤

1. init-build: 下载官方仓库 bigwhite/cbehave（codeload zip）到 $TMPDIR/builds
   - 注意: 上游仓库无 1.0.0 tag（最高 0.2.0），icy/cbehave 原仓库已 404，
     bigwhite/cbehave 为活动维护 fork，按任务要求作为官方源适配为 1.0.0
2. 修复失效辅助脚本: 上游 zip 内 config.guess/config.sub/depcomp/install-sh/missing
   是指向 /usr/share/automake-1.11/ 的绝对路径符号链接，codeload zip 打包后
   退化为 32-37 字节文本占位符，导致 configure 无法运行。
   对策: 从 GNU automake 1.16.5 复制真实脚本替换（已固化为 6 个补丁）
3. configure: `CC=clang ./configure --prefix=$DEFAULT_PREFIX`
4. make: `make -j1`（touch 生成文件时间戳避免 make 误触发 autotools 重生成）
5. make install DESTDIR=$TEST_PREFIX
6. 测试: `make check` 上游未注册测试（TESTS 为空），手动运行 5 个示例测试程序
   （calculator 4/4、string 2/2、product_database 2/2、mock 3/3、text_editor 1/1
   ——text_editor_test 需前置文件 foo.txt，创建后通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压失败 "not a gzip file" | codeload /zip/ URL 返回 Zip 而非 tar.gz，init-build 误判格式 | 用 `--tar zip` 指定格式从 codeload zip 源下载 |
| 2 | 解压失败 "config.guess is a link to an absolute path" | tar.gz 中辅助脚本是绝对路径符号链接，tarfile filter='data' 拒绝 | 改用 zip 源（zip 将符号链接退化为文本占位符，无此安全检查） |
| 3 | configure: no acceptable C compiler | 环境无 cc/gcc，仅有 clang | `export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib` |
| 4 | make: aclocal-1.11: inaccessible or not found | zip 解压后文件 mtime 相同，make 误判待重生成，触发 autotools 重生成链，系统无 aclocal-1.11 | touch aclocal.m4/configure/Makefile.in 等生成文件；配方 build() 中 os.utime 规避 |
| 5 | make check 无测试可跑 | 上游 TESTS 为空，测试程序为 noinst_PROGRAMS 未注册 | 手动逐一运行 5 个测试程序；text_editor_test 需创建前置 foo.txt |
| 6 | refresh-patch 只生成 libtool 补丁 | init-build 以硬链接创建 .work，cp 覆盖源文件污染 .orig，diff 无差异 | 从原始 zip 恢复 .orig 基线后重新 refresh-patch，生成 6 个辅助脚本/平台补丁；libtool 为 configure 生成文件（含主机信息），不固化 |

## 源码修改（补丁清单）

| 补丁 | 内容 |
|------|------|
| 0001-config.guess.patch | 替换失效占位符为 automake 1.16.5 真实脚本 |
| 0002-config.sub.patch | 替换失效占位符为 automake 1.16.5 真实脚本（含 aarch64-unknown-linux-ohos/linux-ohos triplet 支持，去除 android 残留） |
| 0003-configure.patch | configure 临时目录 mktemp 改用 umask 022，规避 HMDFS 上 0700 目录不可写导致 config.status 生成失败（平台适配） |
| 0004-depcomp.patch | 替换失效占位符为 automake 1.16.5 真实脚本 |
| 0005-install-sh.patch | 替换失效占位符为 automake 1.16.5 真实脚本 |
| 0006-missing.patch | 替换失效占位符为 automake 1.16.5 真实脚本 |

## 依赖版本

- GNU automake 1.16.5（辅助脚本来源，仅构建期）
- clang 15.0.4
- 运行期无第三方依赖

## 验证结果

```bash
# 上游 5 个示例测试程序（make check 未注册，手动运行）
src/example/calculator_test        → 3 features/4 scenarios, 0 failed
src/example/string_test            → 1 feature/2 scenarios, 0 failed
src/example/product_database_test  → 1 feature/2 scenarios, 0 failed
src/example/mock_test              → 1 feature/3 scenarios, 0 failed
src/example/text_editor_test       → 1 feature/1 scenario, 0 failed（需前置 foo.txt）
# 合计: 12 scenarios, 0 failed
# test_package/test.c: 消费者视角 4 断言宏 scenarios（conan create 自动执行）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools, 静态库） |
| conandata.yml | 源码 URL + sha256 + 6 个补丁声明 |
| test_package/ | 消费者测试（真实调用 cbehave API + 4 断言宏） |
| patches/ | 6 个辅助脚本/平台适配补丁 |

## 注意事项

- cbehave 是纯 C 静态库（libcbehave.a + cbehave.h/apr_ring.h），无可执行文件交付，
  不需要 commands.json（R38）
- 上游无正式 1.0.0 发布，版本号按任务要求取 1.0.0，来源已在 PR 中如实说明

## 发现与知识积累

- ✅ GitHub codeload zip 打包将指向绝对路径的符号链接（如 config.guess -> /usr/share/automake-1.11/）转为 32-37 字节的文本占位符，解压后需替换为真实 GNU 辅助脚本才能 configure
- ✅ init-build 以硬链接创建 .work 目录，探索阶段 cp 覆盖源文件会同步污染 .orig，导致 refresh-patch 无法识别差异；修改前应先解除硬链接或直接修改后重新恢复 .orig 基线
- ✅ cbehave 上游 make check 未注册任何测试（TESTS 为空），但自带 5 个 noinst_PROGRAMS 示例测试程序，可手动逐一运行验证全部通过
- ✅ cbehave 上游 text_editor_test 需要前置文件 foo.txt，缺失时 FEATURE_RETURN(errno) 返回 ENOENT 导致用例失败，需先创建前置文件
---

**编译结束**: 2026-08-30 19:41
**最终状态**: published
