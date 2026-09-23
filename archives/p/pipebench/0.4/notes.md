# pipebench 0.4 适配笔记

## 编译环境
- 构建系统: makefile（原生 Makefile，无 configure）
- 编译日期: 2026-09-06
- 编译器: clang/clang++
- 状态: built（配方已完成，待 HMBS 真机预检验证后合入）

## 上游信息
- 上游: https://github.com/ThomasHabets/pipebench（作者主页 http://www.habets.pp.se/synscan/）
- 源码包: https://www.habets.pp.se/synscan/files/pipebench-0.40.tar.gz
- sha256: ca764003446222ad9dbd33bbc7d94cdb96fa72608705299b6cc8734cd3562211
- 版本说明: 任务版本号 `0.4` 对应上游 `0.40`（源码内 `static float version = 0.40`，
  tarball 名 pipebench-0.40.tar.gz，内容仅 pipebench.c/Makefile/README/LICENSE/man 页）。
- 许可证: GPL-2.0-or-later（源码头为 GPL-2.0+，LICENSE 文件确认）

## 编译步骤

上游是裸 Makefile 项目，无 configure。配方 build() 中执行：

```bash
make CC="<conan conf c 编译器>" CFLAGS="-Wall -pedantic -O2" -j1 pipebench
./pipebench -h   # 冒烟验证刚构建的二进制
```

package() 不调用 `make install`（上游 install 规则依赖 GNU `install -D`，
OHOS 上不可靠），改为手动 copy：`pipebench` → `bin/`，
`pipebench.1` → `share/man/man1/`，`LICENSE*` → `licenses/`。

## 上游测试审计

- Makefile 无 `check`/`test` 目标；源码树无 tests/ 目录、无 ctest/gtest/pytest 注册。
- 上游 CI 不存在测试流程。结论：上游无测试，按 `no_tests` 处理。
- 证据写入 `test_package/MANIFEST.yml`（`upstream_tests_exist: false` + `upstream_test_audit`），
  build() 与 test_package test() 均输出 `HMBS_UPSTREAM_TEST_RESULT(status=no_tests)` 标记
  （test_package 侧复发是因为包缓存命中时 build() 不执行，保证每轮 evidence 都有标记）。

## test_package 设计（消费者视角，3 个真实用例）

`test_package/test_pipebench.sh` 经 `self.run()` 真实执行被测二进制：

1. `pipebench -h` 退出码为 0 且输出含用法说明（版本横幅 `Pipebench 0.40`）。
2. 管道直通完整性：固定字节流经 `pipebench -q` 后与原文件逐字节一致（`cmp` 校验，
   pipebench 的核心功能就是坐在管道中间转发数据）。
3. `pipebench -Q` 静默模式同样保证直通数据一致。

`test_pipebench.c`（L0c 门禁）通过 `system()` 执行 `<bin> -h` 并校验退出码，
使 CMake 构建的测试目标本身具备独立真实验证能力。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 版本号 0.4 vs 上游 0.40 | 任务要求目录/分支使用 0.4，上游发布为 0.40 | recipe version 取 0.4，conandata 指向官方 pipebench-0.40.tar.gz，并在 notes/manifest 中注明映射关系 |
| 2 | 上游无测试套件 | 单文件基准工具，无测试框架 | 按 no_tests 审计处理；test_package 自建 3 个直通/冒烟用例覆盖核心行为 |

## 依赖版本

无运行时/构建依赖（仅标准 C 库 + POSIX pipe/io）。

## 验证结果

本轮仅完成未提交工作树（按任务要求不本地跑 conan、不 commit、不 push）。
待 HMBS 后台真机预检（conan create 全流程 + test_package + 上游标记）回填实测数据。

## 注意事项

- `install -D` 不可用时不要补装 coreutils，手动 copy 即可。
- pipebench 常驻管道测速时向 stderr 打印进度（含 `\r`），test 用 `-q`/`-Q` 避免干扰 stdout 数据比对。
