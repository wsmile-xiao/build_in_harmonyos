# comptty 1.0.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-10
- 编译器: clang/clang++ (aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. 官方 GitHub tag tarball 下载（v1.0.3），sha256=87c672f3...
2. init-build 解压失败：上游 tarball 的 build-aux/compile 是绝对路径符号链接
   （-> /usr/share/automake-1.15/compile），Python tarfile filter='data' 拒绝
   → conanfile.py source() 中用 Python 内联替换为真实 compile wrapper
3. 官方 tarball 无 configure 脚本（仅 configure.ac + 已生成 aclocal.m4/
   Makefile.in/config.h.in）→ build() 中用系统 autoconf 自举生成
4. configure 失败 "cannot guess build type"：config.guess 2008 版不识别
   HarmonyOS → 0001-build-aux-config.guess.patch 添加 aarch64-HarmonyOS
   分支映射为 aarch64-unknown-linux-gnu（comptext 已合入同款方案）
5. configure 失败 "cannot run C++ compiled programs"：clang++ 链接
   libc++_shared.so 运行时找不到 → LD_LIBRARY_PATH prepend 注入 OHOS SDK
   llvm/lib/aarch64-linux-ohos（子目录必须置前，受控实验验证）
6. config.status 失败 "Permission denied"：autoconf 生成的 configure 中
   mktemp -d + umask 077，HMDFS 上 0700 目录属主映射为 file_manager 不可写
   （E011）→ build() 中 sed umask 077→022
7. configure 成功 → make -j1 → 链接需注入 libfltk/libx11 等依赖 lib 路径
   （LDFLAGS + LD_LIBRARY_PATH）
8. 编译错误 "X11/X.h not found"：xorgproto 传递依赖被 conan 标为
   "Skipped binaries" 不装头文件 → 提升为直接 requires（libfltk 同款修复）
9. 版本号错误（二进制输出 1.0.2）：上游 tarball 自带的过期 src/config.h
   （VERSION=1.0.2）在 VPATH 构建中被"引号 include"优先命中 → source()
   删除残留 config.h，configure 重新生成
10. make check：上游无自带测试（见下），无 check 目标
11. make install DESTDIR 隔离验证通过
12. conan create + test_package 通过（--version 1.0.3 + --help，5 断言全过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压失败 | tarball 中 build-aux/compile 为绝对路径符号链接 | source() Python 内联替换 |
| 2 | cannot guess build type | config.guess 2008 版无 HarmonyOS 分支 | 0001-build-aux-config.guess.patch |
| 3 | cannot run C++ compiled programs | libc++_shared.so 不在运行路径 | LD_LIBRARY_PATH prepend llvm/aarch64-linux-ohos |
| 4 | config.status Permission denied | umask 077 临时目录 HMDFS 不可写 | sed umask 077→022 |
| 5 | X11/X.h not found | xorgproto 传递依赖 Skipped binaries | 提升为直接 requires |
| 6 | 二进制版本号错误(1.0.2) | tarball 自带过期 src/config.h | source() 删除残留 config.h |
| 7 | FL/Fl.H not found | fltk-config 引用 .cache 残留路径 | FLTK_CFLAGS/FLTK_LIBS 手动注入 |

## 源码修改

- patches/0001-build-aux-config.guess.patch：config.guess 添加 HarmonyOS 识别分支
- conanfile.py source() 内联：build-aux/compile 符号链接替换为真实文件
- conanfile.py source() 内联：删除上游 tarball 自带的过期 src/config.h

## 依赖版本

- libfltk/1.3.11（硬依赖，含 libx11/1.8.13 + xorgproto/2025.1 传递依赖）

## 上游测试核查（穷尽）

- 源码包全文件清单：无 tests/ 目录、无 test_*.cxx 源文件
- Makefile.am / src/Makefile.am：无 TESTS / check_PROGRAMS 目标，make check 为空操作
- 上游 git 仓库（github.com/w1hkj/comptty）：仅 6 个提交，无任何测试资产
- 唯一相关文件 data/jabbertest.txt 为运行时示例数据（非测试程序）
- 结论：上游无自带测试 → 自研 test_package/test.sh（--version/--help 断言，
  5 个断言，R34 实质调用被测二进制）

## 验证结果

```bash
# conan create（干净构建 + test_package）
conan create archives/c/comptty/1.0.3 -pr:h=ci/conan/profiles/ohos-aarch64 ...
# 输出: comptty test_package PASS（--version 1.0.3 / --help 2 项断言）
# conan-verify: G0-G4 + L2/L4/L5 全门禁通过
# W3 本地 CI 模拟 (build_and_test.sh): 100% 通过
```

## 注意事项

- 版本号采用 1.0.3：任务指定 1.0.1 在上游 git 历史中从未存在
  （全部 6 个提交版本演变为 1.0.2→1.0.3），经用户确认改用上游实际存在的 1.0.3
- 本软件为 FLTK GUI 应用（X11 后端），沙箱无显示环境，CLI 模式
  --version/--help 可运行（test_package 在 conanrun env 下断言通过）

## 编译结束

comptty 1.0.3 适配完成（最终状态: built），W3 本地 CI 模拟 100% 通过，W4 审计通过。
