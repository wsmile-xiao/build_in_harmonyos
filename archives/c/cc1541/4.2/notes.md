# cc1541 4.2 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

```bash
# 上游源码 as-is 编译与官方测试（设备，源码包 SHA256 见 conandata.yml）
make CC=clang -j1              # 构建 cc1541 二进制
make check CC=clang -j1        # 构建并运行官方 135 用例套件 ./test_cc1541 ./cc1541
```

配方内 `build()` 等价执行 `make all CC=<conf 编译器> -j1`；`CC` 必须显式传入——
上游默认规则使用裸 `cc`，构建主机不存在该名字（R33 从
`tools.build:compiler_executables:c` 获取）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始上游仓库不可达：bitbucket.org/PTV_Claus/cc1541 全部 404 | Bitbucket 以 inactivity 为由停用了该工作区（API 明确返回 deactivated），仓库与下载一并失效 | 改用作者发布 4.2 的官方发布渠道 CSDb（4.2 = release id 240041，作者置顶评论标注取代 4.1 的 release 230166）：https://csdb.dk/getinternalfile.php/254099/cc1541-4.2.zip，SHA256 实测一致 |
| 2 | `make check` 首跑失败 `make: cc: No such file or directory` | check 目标经内置规则编译 test_cc1541，默认 `CC=cc` | `make check CC=clang`（命令行传入，已验证 rc=0） |
| 3 | 配方不能用 `make install` 打包 | 上游 install 规则依赖 coreutils `install`，构建主机无此命令 | `package()` 直接用 `conan.tools.files.copy` 复制单个二进制并保留执行位 |

## 源码修改

无补丁。上游为纯可移植 C99（`io.h`/`windows.h` 均在 `_WIN32` 分支内），
clang 15 `-Wall -Wextra -pedantic` 零警告通过，无需任何源码改动。

## 依赖版本

无依赖（单文件 C 程序，仅 libc）。

## 验证结果

```bash
$ make check CC=clang -j1      # 官方套件，设备实测 2026-09-06
...
Passed 135 of 135 tests.
# rc=0；完整日志为本地工件 reports/upstream-check.log（随仓库惯例不入库），
# 关键证据行已在 PR 正文引用
```

- 上游静态用例总数：135（test_cc1541.c 中 135 个 `++test` 用例块，静态逐个计数）
- 实际执行：135；通过：135；失败：0；跳过：0
- 消费者测试（test_package/test.sh）：4 项断言（版本横幅、D64 生成退出码、
  174848 字节镜像大小、目录项存在），4/4 通过

## 注意事项

- 测试套件必须在源码目录根执行（`./test_cc1541 ./cc1541`，内部用
  `system()` 调用被测二进制并读取 `transwarp v0.84/0.86.prg` 资产）。
- 二进制产物为命令行工具，软件级 `commands.json` 已按 R38 声明。
- 上游 Bitbucket 工作区若由作者恢复/迁移（JackAsser 2026-06 在 CSDb 留言
  拟迁移源码），后续升级版本时应切回官方仓库 URL 并核对新 SHA256。
---

**编译结束**: 2026-09-06 01:26
**最终状态**: built
