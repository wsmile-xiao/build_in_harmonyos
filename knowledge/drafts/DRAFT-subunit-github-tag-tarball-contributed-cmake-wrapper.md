# DRAFT-subunit-github-tag-tarball-contributed-cmake-wrapper — GitHub tag tarball 只有 autotools 输入时的配方自带 CMake 包装(单翻译单元 C 库)

> 来源:subunit 1.4.5 适配(task subunit/1.4.5,自导入)
> 环境:build_in_harmonyos 配方仓库;源为 codeload.github.com tarball(105KB);OH 构建环境无 autoreconf/autoconf 链

## 场景特征

```
源 = GitHub tag tarball(codeload):含 configure.ac / Makefile.am / m4/,
但【没有生成的 configure】——regenerate 需要 autoconf+automake+libtool,
OH buildbot worker 不携带该链;Meson/CMake 类配方模板无处下手。
同时上游 C 库极小:单翻译单元(c/lib/child.c)+ 单头文件(c/include/subunit/child.h)。
```

## 触发条件

- 任务源为 GitHub tag tarball(codeload/github archive),而非 release tarball
  (release tarball 通常自带生成的 configure;tag tarball 不带)
- 上游构建为 autotools,OH 环境无法 autoreconf
- 库体积小(单翻译单元或极少数 .c),手写构建脚本精确可控

## 根因分析

1. **tag tarball ≠ release tarball**:codeload 输出是仓库快照；是否包含
   configure 取决于上游是否将生成物提交到该 tag，不能一概断言“不包含”。
   本次绑定源码未携带 configure，直接套 autotools 配方会在 conan configure 阶段
   "configure: No such file or directory"。
2. 对单翻译单元库,完整 autotools 链提供的可移植性(特性检测)实际未被
   使用(configure.ac 仅做编译器/头文件基础检查);一个十几行的 CMakeLists
   即可精确等价构建,且可评审、可哈希钉死。

## 解决方案

### 推荐方案(配方自带 CMake 包装)
1. 当前配方在 `build()` 内嵌 CMake 包装(add_library 单文件 +
   include 目录 + GNUInstallDirs 安装)。归档中的 cmake/CMakeLists.txt 只是
   可读对照，不由 export_sources 携带；上游产品源码不修改。
2. `build()` 将内嵌包装写入源码根,再走标准 CMake(self) 配置/构建;
   shared/static 双模式,fPIC 惯例处理。
3. `basic_layout(src_folder=".")`(与 libevdev 先例一致)。
4. `test_package` 为真实消费者:CMake find_package 链接,调公开 API,
   断言协议输出;交叉编译时按惯例 build-only 不运行(输出信息声明)。
5. 当前配方通过 test_requires 绑定已发布 Check，编译并执行上游原始
   C/Check 六个测试；使用任务私有 TMPDIR/TEMP，清除框架选择器并验证
   XML 测试身份。不得以缺少宿主 Check 为由把上游测试计为零或跳过。

### 禁止做法
- ❌ 在 CI 上跑 autoreconf(环境无链,且生成的 configure 不可哈希钉死)
- ❌ 提交生成的 configure 进配方(万行生成物,评审灾难)
- ❌ 改上游 Makefile.am 让它"顺便"当 CMake 用

## 验证

```bash
conan create archives/s/subunit/1.4.5 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# native 消费者逐字节验证 subunit v1 流(test:/success: 行)
# 完整原始 C/Check 测试必须实际执行；交叉编译只证明编译和链接。
```

## 关联条目

- 本文为历史构建包装说明，不替代当前 PR 必交的 E2026100501 配对草稿；
  当前真实增量为对 PR #9499 / E571 的框架临时环境与选择器隔离补充。

- 相关:DRAFT-agnostic-lizard-source-only-lisp-package-conan-noarch-integrity
  (零编译姊妹场景;subunit 是"可编译但绕开缺失工具链"的对照场景)
- 相关:libevdev 1.13.4(Meson 模式先例:上游自带 meson.build,无需补脚本)
- 冲突:无
