# DRAFT：上游"测试入口"存在但**自身不可构建**——rule4 少报的两类合法解释与取证方式

> Contributor: CIW ｜ Status: Draft ｜ Updated: 2026-09-21
> Source: mrboom 5.5 适配（PR #11296，rule4 被判 FAIL 后整改）
> 同 stem 知识文件：`DRAFT-mrboom-5.5-upstream-test-entry-unbuildable.kv`

## 错误特征

赛题审查机器人 rule4 判 **FAIL 且提示"少报"**：`上游实测 N=2 > 声明 N=0`，并给出
"上游有用例 2 个但一个也没测（0/2），无论任何理由均不通过"。而按我们的静态清点，
"上游无测试套件"——**两边都没说谎，分歧在于"测试入口存在"与"测试可执行"是两件事**。

## 根因分析

机器人的 `N` 来自**按源码树清点测试入口**（测试目录 / `Makefile.test` / `rxml_test.c` 等），
并不检查这些入口在当前源码包下**能否构建**。于是出现两类"入口存在但不可执行"：

1. **入口依赖 git 子模块，而官方 release tarball 不含子模块内容**（本 PR 入口①：
   `formats/xml/test` 的 Makefile 引用 `../../../../deps/yxml`，官方 `MrBoom-src-5.5.tar.gz`
   未包含 `deps/`）→ `../rxml.c:30:10: fatal error: '../../deps/yxml/yxml.h' file not found`。
   该类已入库：**E150**（manual-download：release tarball 不含 submodule 内容 → 单独下载子模块再拷入）。
2. **上游自带测试与自身源码不同步（签名漂移）**（本 PR 入口②之一：
   `test_stdstring.c:141` 仍按旧 3 参调用 `string_replace_substring`，而头/实现已 5 参）→
   `error: too few arguments to function call, expected 5, have 3`。**该类此前无条目**，本条新增。

关键点：**这是上游自身缺陷，不是适配引入的**；但如果不在 PR 正文里**逐项标注并给出可复现报错**，
审查侧只能看到"声明 N 比实测小"→ 直接按少报判 FAIL。

## 推荐方案

**方法**: enumerate-upstream-test-entries-then-prove-each-unbuildable-one

1. **先按入口把 N 数对**（不要写"上游无测试套件"就完事）：逐个列出可被清点到的测试入口
   （测试目录、`Makefile.test`、含 `main` 的 `*_test.c`），并声明 **N_static = 入口数**。
   本 PR 修正为 `N_static=2`。
2. **能构建的一律真跑**：把入口接进 `build()` 真实编译并运行，把结果写进"适配后测试用例统计"。
   本 PR 入口②的 5 个 Check 单元测试执行 4 个（111/111 断言通过）。
3. **不能构建的逐项取证**：在 PR 正文**单列「未执行测试」表**，每项写明：入口路径 / 原因分类 /
   **官方源码包下的实测报错原文**。子模块类引用 E150；签名漂移类按本条口径。
4. **禁止**为了让分母好看而删入口数或谎报执行数；也不要用"上游无测试"一句话带过。

**验证/命令**

```bash
# ① 数入口：找含 main 的测试程序与测试 Makefile
grep -rl "int main" --include="*_test.c" --include="test_*.c" . | sort
find . -name "Makefile.test" -o -name "test" -type d | sort
# ② 逐项试构建，保留第一条真实报错（官方 tarball 原样，不打补丁前）
#   子模块缺失 → 形如 "'../../deps/xxx/xxx.h' file not found"
#   签名漂移   → 形如 "too few arguments to function call, expected 5, have 3"
```

## 适用范围与反例

- **适用**：任何"上游自带测试套件"的包，尤其从 GitHub **release tarball / archive** 取源的
  （子模块内容通常不在包内）；以及长期未维护、测试与源码一同漂移的老库。
- **反例/边界**：
  - 子模块缺失**不等于可以不做**——优先按 E150 单独取子模块后真实执行；只有确认无法取得/按 §9
    不允许捎带第三方源码时，才记为未执行并取证。
  - "签名漂移"必须证明是**上游自身**问题：给出头文件签名与调用点的对照（本 PR 给
    `include/string/stdstring.h:162` vs `test/string/test_stdstring.c:141`），且**不修改上游测试**。
  - 不要把"我们不想跑"归类为"入口不可构建"——证据必须是官方源码包下的构建报错。

## 验证证据（mrboom 5.5 / PR #11296）

- 入口① `formats/xml/test`：`../rxml.c:30:10: fatal error: '../../deps/yxml/yxml.h' file not found`
  （官方 tarball 无 `deps/`；该类已入库 E150）。
- 入口② `Makefile.test`：`test_utils`(3 断言) / `test_hash`(3) / `test_linked_list`(89) /
  `test_generic_queue`(16) 真实执行，Check 输出 `100%: Checks: N, Failures: 0, Errors: 0`（**111/111**）；
  `test_stdstring` 编译失败 `error: too few arguments to function call, expected 5, have 3`（上游漂移）。
- 修正后 PR 正文：上游 `N_static=2`、适配后合计 5 个程序，并附「未执行测试」证据表。
