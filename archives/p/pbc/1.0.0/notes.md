# pbc 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

配方从 Stanford 官方正式源码包构建，补入上游版本库固定的 GoogleTest
`86add13493e5c881d7e4ba77fb91c1f57752b3a4`，应用可移植性补丁后执行
`./configure --enable-cxx --enable-shared --disable-static`、`make`、
`make check VERBOSE=1` 和 `make install`。GMP、Flex、Bison 均由 Conan 提供。

## 上游测试清点（R51）

上游 `Makefile.am` 注册 `gtest` 与 `pbc_test` 两个 `TESTS` 程序；源码目录
`unittests/` 没有其他独立测试入口。GoogleTest 运行时展开数量如下：

| 测试程序 | 测试源码 | 运行时用例数 | 执行命令 |
|----------|----------|-------------|----------|
| `gtest` | `unittests/gtest.cpp` | 1 | `./gtest --gtest_brief=1` |
| `pbc_test` | `unittests/pbc_test.cpp` | 133 | `./pbc_test --gtest_brief=1` |
| **合计** | | **134** | `make check VERBOSE=1` |

宿主基线与 OHOS arm64 目标程序均实际运行 134/134，通过率 100%；补丁未修改
任何测试文件。消费者测试另含 16 个公开 C/C++ API 断言，实际运行 16/16。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 正式源码包无法构建上游测试 | 上游以 git submodule 管理 GoogleTest，正式 tarball 中该目录为空 | 按 PBC 1.0.0 提交的 gitlink 固定值下载 Google 官方提交归档 |
| 2 | 源码树内编译 `pbcxx.h` 找不到 `pbc/pbc.h` | 该包含路径只符合安装后的目录布局 | 改为同目录引号包含 `pbc.h`，同时兼容源码树和安装目录 |
| 3 | 现代 C++ 编译器拒绝 `ElementWrapper` 访问 `Pairing::pairing_` | 匿名命名空间中的模板不能由外层命名空间的友元模板声明匹配 | 将两个包装模板置于 `pbc` 命名空间，使声明与定义匹配 |
| 4 | `configure` 误报 Flex 不可用 | `AC_PROG_LEX` 不仅运行 Flex，还链接 `-lfl` 检查 `yywrap`，构建工具的库目录默认不进入目标链接参数 | 从 Conan build-context 的 Flex 包取得库目录并前置到 `LDFLAGS` |
| 5 | 源外构建找不到 `pbc_utils.h` | 上游各目标使用 `-I include`，未将该相对路径锚定到源码目录 | 将 Conan build 目录设为源码根，按上游支持的源码内模式构建 |
| 6 | 消费者包含 `pbc.h` 时找不到 `gmp.h` | PBC 的公开头直接暴露 GMP 类型，依赖头和库必须向下游传递 | 将 GMP requirement 标记为传递头文件和传递库依赖 |
| 7 | HarmonyOS CI 的 `config.guess` 在 `$TMPDIR/cgXXXXXX/dummy.c` 报 `Permission denied` | HMFS 对 `umask 077` 创建的目录产生异常权限，且上游脚本不识别 `HarmonyOS`，因而落入编译探针 | 为 `config.guess/config.sub` 增加 `linux-ohos` 原生识别，并将 `configure` 内 `config.status` 临时目录的 umask 调整为 022 |

## 源码修改

`0001-include-pbcxx.h.patch`：修复 C++ 公共头的包含路径和模板友元可见性；
不引入平台宏，不修改上游测试用例。

`0002-autotools-harmonyos.patch`：让 Autotools 配置脚本原生识别 HarmonyOS，
同时修复 HMFS 上 `umask 077` 临时目录不可写的问题；未使用伪造的
`--build/--host` 参数，也未修改或跳过上游测试。

## 依赖版本

- gmp/6.3.0
- flex/2.6.4.2（构建工具）
- bison/3.8.2（构建工具）
- GoogleTest git commit 86add13493e5c881d7e4ba77fb91c1f57752b3a4（上游固定测试子模块）

## 验证结果

```bash
make check VERBOSE=1
# 上游测试程序 2/2；展开测试用例 134/134，通过率 100%

conan create archives/p/pbc/1.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# PBC 库构建、上游测试和 test_package 消费者测试全部通过
```

共享库与 `shared=False` 静态库配置均完成 OHOS arm64 构建、安装及消费者运行验证。

## 注意事项

`pbc::Pairing` 必须比由它初始化的 C++ 元素对象存活更久。默认构建共享库；
`shared=False` 可生成静态库。
---

**编译结束**: 2026-09-09 06:22
**最终状态**: built
