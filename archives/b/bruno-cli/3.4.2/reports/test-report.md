# bruno-cli 3.4.2 测试报告

- 日期: 2026-09-18
- 环境: OpenHarmony PC (aarch64), Node.js v24.13.0 (OHOS), npm 11.6.2, conan 2.29.1
- Profile: ohos-aarch64 (os=OHOS, arch=armv8, clang 15, libc++, Release)

## 本地 W3 CI 模拟（ci/conan/build_and_test.sh archives/b/bruno-cli/3.4.2）

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: bru.js --version OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Total: 1, Success: 1, Failed: 0
```

- `conan create` 通过：源码从 registry.npmjs.org 下载校验通过；`npm install --ignore-scripts` 安装 365 个依赖约 1 分钟
- L1 破坏性反向验证（R34）：移走 bin/ 与 lib/ 后测试失败，确认测试实质依赖被测包

## test_package 消费者测试（test.sh，3 项断言）

```
$ bru --version
3.4.2

$ bru --help
Bru CLI 3.4.2
Usage: bru.js <command> [options]
Commands:
  bru.js import <type>   Import a collection from other formats
  bru.js run [paths...]  Run one or more requests/folders

bruno-cli consumer tests passed
```

1. `--version` 输出精确等于 `3.4.2`
2. `--help` 含 `run` 子命令
3. `--help` 含 `import` 子命令

## 上游测试清点（R51）

上游包 `@usebruno/cli@3.4.2` 的 npm tarball 仅含 31 个文件（bin/ + src/），无 tests/ 目录；
上游测试脚本 `npm test` 为 `node --experimental-vm-modules $(npx which jest)`，但 tarball 内
未随包分发测试文件（测试套件位于 usebruno/bruno 仓库 monorepo 其他包中，不随 cli 包发布）。
上游确无可运行测试，以 test_package 3 项断言替代覆盖。

## 结论

本地 W3 CI 模拟全部通过，具备提 PR 条件。
