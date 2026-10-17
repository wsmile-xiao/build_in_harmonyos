# E543 — gp 单进程内 nflist 表状态污染：批量 QT 查询使后续 A5 精确计数断言假失败

> 草稿条目（`draft: true`，贡献者 `B5C8`，源自 pari-nflistdata/20220729 适配）。
> 结构化字段见同名 `E543-draft-B5C8.kv`；本文件是配套人类可读文档（W5 要求 doc↔kv 配套）。

## 错误特征

在同一份 GP 脚本里先跑批量 `nflist([deg,idx],'t)` 断言、再跑 A5 表的精确计数断言时，
后者无条件失败，而数据本身完好：

```
qt_15_104 PASS
…（前序 650 条 QT 断言全部 PASS）
a5_r2_0_full_table FAIL      ← #A5F 不再等于 15184
a5_r2_0_subrange_monotone FAIL
gp_rc=0                      ← 注意：gp 仍返回 0，属静默假失败
```

把同一族断言单独放进一个 gp 进程执行时，`nflist("A5",[1,524286^2],0)` 稳定返回 15184
（= `5/4/0/{0..5}` 六个分片共 15185 行减去末片哨兵 `[0,0]`），断言 PASS。

## 触发条件

- 构建系统: 无（纯数据包；触发点在**测试驱动**侧）
- 阶段: test（上游功能入口实跑）
- 宿主: 制品仓 `pari/2.17.4.1`（及同版本线）的 `gp`，OHOS arm64 与 Linux 侧同现
- 诱因: 一个 gp 进程内混跑「不同数据族」+「依赖表内容规模的精确计数断言」

## 根因分析

`nflist` 在 gp **进程内**维护已加载数域表的内部状态（QT 检索路径与 A5 检索路径共享该状态）。
先执行 650 次 `nflist([deg,idx],'t)` 会改写这份内部状态，导致随后的
`#nflist("A5",[1,524286^2],0)` 取到被污染的子集，返回值规模不再等于表内数据行数。

关键判据（用于把它与"打包/数据错误"区分开）：**同一脚本对上游原始解包目录与
conan 打包产物表现完全一致（同样 2 项 FAIL）** ⇒ 不是打包差异、不是数据损坏，
而是解释器进程内的状态问题。若误判为打包问题，会去改配方或加补丁，方向完全错。

## 解决方案

### 推荐方案（rec_priority: 1，`rec_auto_fix: false`）

测试驱动**按断言族拆分进程**：每个 family 单独生成 GP 脚本、各起一次 gp，
再由外部驱动合并逐用例结果并与"期望用例清单"比对（清单里有、日志里没有 ⇒ 判 FAIL）。

```bash
for fam in qt a5; do
  python3 upstream-gp-sweep-generator.py <datadir_root> --family $fam --out sweep-$fam.gp
  gp -q -f sweep-$fam.gp
done
# 或直接使用本包驱动：run-upstream-gp-sweep.py（内建分进程 + 缺失即 FAIL + 归因阶段）
```

生成器保留 `--family` 开关，使任一族都能单独复现；驱动负责合并与核对，
不依赖 gp 退出码判断整轮结果（gp 在断言失败时仍返回 0）。

### 禁止做法

- ❌ 把不同数据族的断言塞进同一个 gp 进程"省启动开销"（gp 启动仅 ~0.25 s，
  省下的开销远小于一次误判返工的代价）。
- ❌ 为了让断言"通过"而把期望值改成污染后的实测值 —— 那是把测试迁就 bug，
  且换台机器/换顺序就会再翻车。
- ❌ 看到该 FAIL 就去改 `package()` 的数据布局或给上游数据打补丁（R6：探索阶段
  不动源码；此处根因根本不在源码）。
- ❌ 只看 `gp_rc=0` 就认定整轮测试有效（0 用例/静默失败必须靠"期望清单核对"兜住）。

## 验证

```bash
# 被审对象：本包 conan create 产物；期望 TOTAL=685 PASS=665 FAIL=0 SKIP=20、driver rc=0
python3 run-upstream-gp-sweep.py <pkg>/res/pari \
    --gp  <pari>/bin/gp --lib <pari>/lib --lib <gmp>/lib \
    --out-cases upstream-test-cases.txt

# 反向证伪（证明污染来自同进程顺序，而非数据）：
python3 upstream-gp-sweep-generator.py <pkg>/res/pari --family all --out sweep-all.gp
gp -q -f sweep-all.gp          # → a5_r2_0_full_table FAIL（复现污染）
python3 upstream-gp-sweep-generator.py <pkg>/res/pari --family a5 --out sweep-a5.gp
gp -q -f sweep-a5.gp           # → a5_r2_0_full_table PASS（分进程即恢复）
```

## 关联条目

- 相关: E429（同族 pari-galpol 记录的 GP 批处理两坑：注释行尾反斜杠被当续行；
  该 gp 构建无 `file_exists`/`is_file`/`is_dir`/`wildcards` 文件系统原语）——
  同属「gp 侧能力边界决定测试驱动必须把枚举/判定放在外部脚本」这一族结论。
- 适用包: pari-nflistdata（`nflist`）、pari-galpol（`galoisgetpol`）、
  pari-elldata（`ellinit`/`ellsearch`）、pari-seadata（`ellmodulareqn`/`ellap`）
  等一切以 gp 批量断言验证的 PARI 系数据包。
