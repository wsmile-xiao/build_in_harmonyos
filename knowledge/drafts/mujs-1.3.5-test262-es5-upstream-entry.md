# mujs（嵌入式 JS 解释器）：Makefile 构建 + test262 ES5 上游测试入口

> 草稿（DRAFT）。与同目录 `mujs-1.3.5-test262-es5-upstream-entry.kv` 成对。

## 现象

适配 mujs 1.3.5 到 OHOS 时：
1. `conan create` 报 `No rule to make target 'release'`——conan 在 build 目录执行 make，
   而 mujs 的 Makefile 在 source 目录且**无 configure 脚本**；
2. 系统缺 readline 头/库，直接构建报 readline 缺失；
3. 官方测试入口不是 `make check`，而是 `tools/test262` runner + `tools/test262-harness.js`
   配合外部 ECMAScript ES5 一致性套件；
4. `mujs --version`/`--help` 均报 `unknown option`（mujs 只支持 `-i`/`-s`）。

## 根因

- mujs 是纯 Makefile 构建的嵌入式 JS 解释器（无 configure），conan 配方须
  `self.run(..., cwd=self.source_folder)` 指定源码目录执行 make；
- readline 是可选依赖，OHOS 无该库时须 `HAVE_READLINE=no` 禁用；
- 上游官方测试 = test262 ES5 一致性套件（tc39/test262 es5-tests 分支，11724 用例），
  每个用例独立进程运行 harness（防全局状态污染）；
- mujs CLI 的 getopt 只有 `-i`/`-s`，无版本/帮助选项，L2 smoke 用真实 JS 脚本验证。

## 判据

- 构建：`make release HAVE_READLINE=no CC=clang AR=llvm-ar -j1`（R33：编译器取自 Conan conf）；
- 测试统计以**全量发现数为分母**：11724 用例、通过 9636、失败 581、跳过 21（上游 KNOWN_BAD
  挂起），全量通过率 82.19%；失败均为 mujs ES5 子集实现差异（Intl 未实现、'length'
  只读、严格模式抛错差异），非 OHOS 平台引入；
- API 验证注意：`js_dostring` 不保留表达式栈值，须经全局变量（`js_getglobal`）读取结果。

## 快速命令

```bash
git clone --depth 1 --single-branch --branch es5-tests https://github.com/tc39/test262.git
make release HAVE_READLINE=no CC=clang AR=llvm-ar -j1
tools/test262 <test262-root>/test/suite          # 全量 ES5 套件
mujs smoke.js                                    # CLI 端到端（无 --version）
```

## 适用范围

嵌入式 JS 解释器类库（mujs 及同类）在 OHOS 上的适配；特别适用于带官方 test262
一致性套件入口、无 configure 的纯 Makefile 项目。

## 证据（mujs 1.3.5，pc3-1，OHOS arm64）

- `make release HAVE_READLINE=no` 编译通过；staging 产物
  `bin/mujs`、`bin/mujs-pp`、`lib/libmujs.a/.so`、`include/mujs.h` 齐全；
- test262 es5-tests 全量 11724：通过 9636 / 失败 581 / 跳过 21，
  全量通过率 9636/11724 = 82.19%，实际执行集合通过率 94.31%；
- `conan create` 干净构建 G2 通过；test_package 真实 API 测试 + CLI smoke 通过；
- W3 本地 CI 模拟 L0-L5 全绿（100% pass rate）。
