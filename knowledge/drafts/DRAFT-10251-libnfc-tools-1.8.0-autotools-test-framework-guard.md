# DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard：上游测试套件被 configure 守卫静默排除（make check 报 TOTAL: 0）——先判「没跑」再补框架

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-16
> Source: libnfc-tools 1.8.0 适配（PR #10251）；触发场景：审查判「上游有用例 6 个但一个也没测（0/6）」
> 对应：`knowledge/drafts/DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard.kv`

## 现象

上报「上游测试用例通过率」时，`make check` 看上去"全部通过"，实际一个用例也没编译：

```text
Making check in test
make[2]: Entering directory '.../libnfc-1.8.0/test'
make[2]: Nothing to be done for 'check'.
make[2]: Leaving directory '.../libnfc-1.8.0/test'
...
# TOTAL: 0
# PASS:  0
```

**迷惑点（两种误判方向）**：

| 误判 | 表现 | 后果 |
|------|------|------|
| 当成"上游测试全过" | 退出码 0、无 FAIL 行 | PR 里写"上游 6/6 通过"，实为 0/6 → 审查判少报/谎报 |
| 当成"该平台跑不了测试" | 归因平台限制/无环境 | 审查判「硬性不通过」，因为平台限制不是理由 |

真相介于两者之间：**测试目标根本没进构建**——不是通过、也不是失败，是*不存在*。

上游 `test/Makefile.am` 把 6 个用例整个包在条件块里：

```makefile
if WITH_CUTTER
cutter_unit_test_libs = test_access_storm test_dep_active test_dep_passive \
                        test_device_modes_as_dep test_register_access test_register_endianness
endif
```

## 根因（机制链，与目标平台无关）

```
configure.ac:  AC_CHECK_CUTTER([>= 1.1.7])       ← 探测 cutter 框架
        │
        ├─ 找到 → WITH_CUTTER=yes → AM_CONDITIONAL 为真 → test/ 目标生成 → 用例进构建
        └─ 缺失 → WITH_CUTTER=no  → AM_CONDITIONAL 为假 → test/ 目标为空
                                                          │
                                                          └─ make check 无目标可做 → "Nothing to be done" → TOTAL: 0
```

关键性质：**这是 autotools 的"优雅降级"设计，不是报错**。configure 不会失败
（框架是可选构建依赖），所以整条链在日志里只留下 `TOTAL: 0` 这一处指纹，
且被埋在 `make check` 的常规输出里（退出码 0，CI 不会红）。

`AC_CHECK_CUTTER` 出自 `cutter.m4`（ClearCode/Cutter 随包提供的宏），同类守卫还有
`AC_CHECK_LIB`/`PKG_CHECK_MODULES` + `AM_CONDITIONAL` 的组合形式，以及
`AX_...` 系第三方宏——判定方法相同：**看 `config.log`/`config.status` 里的条件变量，
不要看 `make check` 的退出码**。

同理适用于其他"可选测试框架"：`check`（libcheck）、`cutter`、`cmocka`、
`cppunit`/`cpputest` 等，只要上游用 `--enable-*` / autodetect 守卫。

## 判别（三步，先定性再动手）

```sh
# 1) 拿 `make check` 的 TOTAL/PASS 计数——TOTAL: 0 就是本模式指纹
make check 2>&1 | grep -E '^# (TOTAL|PASS|FAIL|XPASS|XFAIL)'

# 2) 查条件变量：框架探测结果
grep -E 'WITH_CUTTER|HAVE_CUTTER' configure | head -3      # 宏名以 configure.ac 为准
grep -E '^WITH_CUTTER' config.status 2>/dev/null           # 或 config.status 里的条件快照

# 3) 查构建目标是否为空（决定性证据）
grep -n 'cutter_unit_test' test/Makefile                   # 有变量定义
grep -n '^check_PROGRAMS\|^TESTS' test/Makefile            # 为空 = 目标未生成
```

三步结论只可能是三种之一，处置动作完全不同：

- **① 框架缺失（本模式）** → 补齐框架后重建（见下节）；
- **② 测试确实存在但全被 skip/omit** → 看 `cut_omit`/`SKIP` 语义，属"行内跳过"，
  如实按框架语义上报（Cutter 的 OMIT 非 FAIL，计入 passed）；
- **③ 上游确实没有测试** → 附清点证据（`TESTS=`/`*_test` 目标数 = 0），
  在 PR 里说明"上游无测试"，不得编造通过率。

## 方案（补齐测试框架 → 真实执行，不改上游测试）

以 Cutter 1.2.6 在 HarmonyOS PC（OHOS clang 15.0.4 + musl + 制品仓 glib/2.84.0）
真机交叉编译为例：

1. **取带 configure 的发行包**：Cutter 的 GitHub 镜像树**不含 autoconf 产物**，
   设备上无系统 automake/libtool 时无法 `autoreconf`；改用 SourceForge release
   tarball（自带 `configure`/`aclocal.m4`/`config/ltmain.sh`）。
2. **补 autotools 三元组**：老版 `config.sub`（2016-11-04）不认 `ohos` →
   `system 'ohos' not recognized`；在 `config.sub` 加 `linux-ohos` 分支、
   `config.guess` 加 `*:HarmonyOS:*:*` 分支（与 libnfc 配方同思路）。
3. **按依赖顺序构建**：`m4macros → glib-compatible → gcutter → cutter`——
   libcutter 链接依赖 gcutter，顺序错了报 `No rule to make target '../gcutter/libgcutter.la'`。
4. **运行期把 soname 软链实体化**（见 E505/E492 同族）：libtool 产的
   `libcutter.so.0` 是指向 `libcutter.so.0.1.0` 的**符号链接**，OHOS musl 加载器
   不识别该别名（报 `Error loading shared library libcutter.so.0` 且 reason 为空——
   同一 `.so` 用 `ctypes dlopen` 却成功，是主要烟幕）；
   `cp -f libcutter.so.0.1.0 libcutter.so.0` 替换为实体文件后 `cutter --version` 正常。

完整 9 项踩坑与可复现脚本见归档：
`archives/l/libnfc-tools/1.8.0/upstream-tests/`（`CUTTER-BUILD.md` /
`build_and_run_upstream_tests.sh` / `README.md`）。

> 也可用 conan `tool_requires` + 自写 Cutter 配方替代手工交叉编译，
> 但 Cutter 1.2.6 无公开 conan 配方，需自行封装；手工路径已验证可复现。

## 验证（真实证据）

libnfc-tools 1.8.0，上游 `test/*.c` **原始文件未做任何修改**，真机编译执行：

```text
# libnfc 1.8.0 / test: 6 个 Cutter 用例
3 test(s), 0 failure(s), 0 error(s), 6 omission(s), 100% passed
```

- 6 个用例全部**编译成功并进入 runner**（`built: 6 / executed: 6`）；
- 6 个 omission 全部来自用例内置的 `cut_omit()` 保护（"No NFC device found" /
  "At least two NFC devices must be plugged-in"）——**无 NFC 读卡器硬件时按上游
  设计优雅跳过**；Cutter 语义下 OMIT 非 FAIL，计入 `100% passed`；
- `0 failure / 0 error`；CI 复跑绿（build #48683，全步骤通过）。

## 适用边界与反例

- **触发面**：任何上报"上游测试通过率"却得到 `TOTAL: 0`（或远小于清点数的 N）的
  autotools/CMake 项目——本题是 autotools + Cutter，机制与 `check`/`cmocka`/
  `cpputest` 等可选框架守卫同构（CMake 侧对应 `find_package` 失败导致的
  `BUILD_TESTING` 静默关闭）。
- **反例 1**：`TOTAL` 非 0 但有 FAIL → 那是"跑了但失败"，属
  `DRAFT-celero-2.10.0-upstream-test-debt-triage`（三模式定性法）的适用面，
  不要用本条掩盖。
- **反例 2**：自行把 `WITH_CUTTER` 强改为 yes / 手写 stub 让用例"看起来跑过" →
  **禁止**（R8 精神：空壳 = 功能缺失、谎报测试）。必须让真实框架跑真实用例。
- **反例 3**：测试跑不动就写"平台限制" → 审查明确不接受（"无论任何理由均不通过"）；
  必须先排除本模式，再谈其他技术原因。

## 关系

- **互补**：`DRAFT-celero-2.10.0-upstream-test-debt-triage`（60/67，跑了但失败）
  ↔ 本条（0/6，根本没跑）——构成"上游测试二态判别"：先分清"没跑 / 跑了",
  再进各自的定量/定性流程。
- **家族**：`DRAFT-ohos-glib-test-framework-cmake-inject`（CMake + GLib 测试框架变量注入）
  与本条同属"让上游测试框架真正跑起来"适配链，形态不同（CMake 注入 vs autotools 守卫 + 交叉编译框架）。
- **复用既有节点**：`E505`（OHOS loader 不解析 soname 符号链接别名）、
  `E492`（实体化 Meson soname 别名）——本条 Cutter 场景是其在 **autotools/libtool**
  产物上的又一实证；`DRAFT-ohos-intltool-toolchain-stub`（intltool 工具链 stub）
  同样是 Cutter 交叉编译链上的前置坑，不再重复登记。

## 查重

按 `TOTAL: 0` / `WITH_CUTTER` / `AM_CONDITIONAL` / `Nothing to be done for 'check'` /
`cutter` / `上游测试.*0/` 检索 `knowledge/graph/` 与 `knowledge/drafts/`：

- `cutter` 仅在 `knowledge/operations/build-systems.md` 出现（一般性提及），**无专属节点**；
- `AM_CONDITIONAL`/`WITH_CUTTER` 无既有条目命中；
- 最接近的两条为 celero（跑了但失败）与 glib-test-framework-cmake-inject（CMake 形态），
  均非"测试套件被守卫静默排除"机制 → **本条为新增方法论条目**；
- soname 部分已有 E505/E492，本条内**只做引用不重复登记**。

机器预审证据（`ohc draft-review`，2026-09-16）：

```text
质量预检: signature=✅  root_cause=✅  rec=✅
相似正式条目 TOP5:
  E490  score=0.06  (sig=0.0 kw=0.06 cat=0.12)
  E228  score=0.06  (sig=0.0 kw=0.08 cat=0.14)
  E465  score=0.05  (sig=0.0 kw=0.0  cat=0.29)
  E054  score=0.04  (sig=0.0 kw=0.08 cat=0.0)
  E232  score=0.04  (sig=0.0 kw=0.0  cat=0.14)
📌 预审建议: create —— 疑似新知（无高相似条目）
```

最高相似度 0.06，远低于 0.55 的"疑似重复"阈值，与人工查重结论一致。
（下一步人工纳入：`python3 scripts/ohc-run.py graph promote 10251-libnfc-tools-1.8.0-autotools-test-framework-guard`）
