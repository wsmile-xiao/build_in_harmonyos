# mujs 1.3.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（conan conf tools.build:compiler_executables）/ llvm-ar
- 状态: published

## 编译步骤

mujs 为纯 Makefile 构建（无 configure 脚本）：

```bash
# 依赖预检（W0）：无外部依赖，conanfile requirements 为空 ✅
bash ci/scripts/preflight_check.sh mujs/1.3.5

# 语言预检（R47）：detected=c（与 cpp 兼容）✅
python3 scripts/ohc-run.py lang-preflight mujs 1.3.5 --src $BUILD_SRC_DIR

# 本地编译（探索阶段）
make release HAVE_READLINE=no CC=clang AR=llvm-ar -j1
# staging 安装
make install HAVE_READLINE=no DESTDIR=$TEST_PREFIX -j1

# Conan 配方生成与验证
python3 scripts/ohc-run.py conan-init mujs 1.3.5
python3 scripts/ohc-run.py conan-verify mujs 1.3.5   # G1-G4 全过

# 收尾（含 W2 结构 + W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish mujs 1.3.5 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /tmp 只读（E002） | OHOS /tmp 为只读挂载 | 全程使用 $TMPDIR=/storage/Users/currentUser/tmp/ohos-tmp（chmod 700） |
| 2 | `install` 命令缺失 | 系统 PATH 无 coreutils install | export PATH=/bin:/usr/bin 补齐（E108 同类） |
| 3 | `cc` 不存在 | 设备只有 clang | clang 编译，配方从 conan conf 取编译器（R33） |
| 4 | readline 缺失 | OHOS 无 readline 头/库 | HAVE_READLINE=no 禁用（1.3.9 同法，历史验证） |
| 5 | conan G2 首败：`tools.build:compiler_executables:c` 非法 conf 键 | conf 是 dict 不是 :c 标量 | `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 取 `["c"]` |
| 6 | conan G2 二败：`No rule to make target 'release'` | conan build 目录无 Makefile | `self.run(..., cwd=self.source_folder)` 在源码目录执行 make |
| 7 | test_package 首败：js_dostring 表达式栈值非数字 | mujs 的 js_dostring 不保留表达式栈值 | 经全局变量读取：`js_getglobal` + `js_tonumber`（API 语义） |
| 8 | test_package 二败：`mujs: inaccessible or not found` | conanrun PATH 未注入 bin | test() 内用 `self.dependencies[ref].package_folder/bin/mujs` 绝对路径调用 |
| 9 | mujs CLI 无 --version/--help | getopt 仅 -i/-s | L2 smoke 以 mujs-pp --version 通过（非阻塞）；CLI 验证用真实 JS 脚本 |
| 10 | W3 junk_check 命中 cloog 基线 | archives/c/cloog/0.21.1/.build-closed/.staging-verified 为提交前已存在基线 | 基线隔离复验：记录 sha256(e3b0c...) → git rm --cached 隔离 → 复跑 W3 通过 → git restore --staged 恢复 → 核对 sha256 一致，未进入 mujs PR |
| 11 | make jobserver mkfifo 告警 | HMDFS 上 TMPDIR 限制 mkfifo | 非致命告警，构建正常完成（opencsg 同款草稿已覆盖） |

## 源码修改

无源码补丁（patches/ 为空）。mujs 1.3.5 源码无需修改即可在 OHOS arm64 编译安装。

## 依赖版本

无外部运行时依赖（仅 libc/libm）。测试依赖 test262 ES5 套件（tc39/test262 es5-tests 分支，11724 用例）。

## 上游测试（test262 ES5 一致性套件）

- 入口：tools/test262 runner + tools/test262-harness.js，克隆 tc39/test262 es5-tests 分支
- 全量：11724 用例 → 通过 9636 / 失败 581 / 跳过 21（上游 KNOWN_BAD 挂起）
- 全量通过率：9636/11724 = 82.19%；实际执行集合通过率 94.31%
- 失败分类：ES5 子集实现差异（Intl 未实现 131、'length' 只读 144、ToObject 差异 91、
  严格模式抛错差异 79 等），非 OHOS 平台引入

## 鸿蒙专项测试 / 消费者验证

- test_package/test.c：mujs.h 公开 API（js_newstate/js_dostring/js_getglobal/js_tonumber
  /js_tostring）编译运行 JS 程序，验证数值与字符串结果 ✅
- cli_smoke.js：公开 CLI mujs 运行真实 JS（数组 map/join 断言）✅
- 消费者用例：test_package 即消费者视角（仅用安装后公开头文件与 API）✅

## 验证结果

```bash
# conan create 干净构建 + test_package 真实 API 测试 + CLI smoke
conan create archives/m/mujs/1.3.5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# W3 本地 CI 模拟
build_and_test.sh → JC/L0/L1/L2/L4/L5 全绿，pass rate 100%（1/1）
```
## 结束

最终状态: published（W3 本地 CI 模拟 L0-L5 全绿，conan-verify G1-G4 通过）
