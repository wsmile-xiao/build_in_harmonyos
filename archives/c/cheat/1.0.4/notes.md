# cheat 1.0.4 适配笔记

## 编译环境
- 构建系统: header-only（上游 makefile 仅构建 example/examples 演示驱动）
- 编译日期: 2026-09-19
- 编译器: /data/service/hnp/bin/clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

cheat 是纯头文件 C 单元测试框架（cheat.h 为核心头，配合 cheats.h / windowed.h），
零第三方依赖，仅使用 C 标准库。Conan 配方按 header-library 打包：

1. `conan create` 自动下载官方 tarball（sha256 已核验）并解压；
2. `build()` 内跑上游测试门禁：`tests/*.c` 共 25 个独立测试文件逐一
   用当前 clang 编译并以 `-s` 运行（与上游 `test` 脚本同构）；
3. `package()` 安装 3 个头文件到 include/ 根目录 + LICENSE；
4. test_package 消费者测试编译并运行 3 个 CHEAT_TEST 断言用例。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 执行环境无法直连 github.com | 使用知识库记录的 ghfast.top 镜像下载官方 tarball，sha256 核验一致 |
| 2 | /tmp 只读 | 平台 E002 已知陷阱 | 全部临时产物放 $HOME/tmp 可写目录 |
| 3 | init-build 误判 autotools | URL 形似 archive 包 | manifest build_system 修正为 header-only，配方手工按 header-library 编写 |

## 源码修改

无补丁（纯头文件库，无需修改源码）。

## 依赖版本

- 无第三方依赖；仅 C 标准库（ctype/errno/limits/setjmp/signal/stdarg/stddef/stdio/stdlib/string）
- 工具链: clang 15.0.4 (aarch64-unknown-linux-ohos)

## 验证结果

```bash
# 上游冒烟（成功/失败路径）
clang -I . -w tests/successful.c && ./a.out -s
# "1 successful of 1 run / SUCCESS" rc=0
clang -I . -w tests/failed.c && ./a.out -s
# "1 failed of 1 run / FAILURE" rc=1
# make build 演示驱动
make build CC=clang  # example / examples 构建通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library），build() 内含上游测试门禁 |
| conandata.yml | 官方 tarball URL + sha256 |
| test_package/ | CMake 消费者测试（3 个 CHEAT_TEST 真实断言） |
| MANIFEST.yml | 上游测试声明 |

## 注意事项

- cheat.h 要求 `__BASE_FILE__` 预定义（clang 自动提供），消费者直接
  `#include <cheat.h>` 即可，无需额外宏。
- 测试二进制退出码：全部通过 rc=0，任一断言失败 rc=1（上游 `test`
  脚本与 `make test` 均依赖此语义）。
- commands.json：本库为纯库类型（header-library），无 CLI 产物，按 R38
  不需要声明 commands.json。
---

**编译结束**: 2026-09-19 01:29
**最终状态**: built
