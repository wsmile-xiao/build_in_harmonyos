# DRAFT-pd-external-headless-host-load-verification — 宿主加载型插件怎么用真机宿主无头验证

> 配套第一稿：`DRAFT-pd-external-host-sdk-header-resolution`（头目录/扩展名从哪来）。
> 本稿解决**插件装好之后如何证明「宿主真的能加载并正确运行」**，以及一个会让人
> 误判为失败的**输出竞争**坑。

## 错误特征（可粘贴的真实日志）

```
pd: command not found
couldn't create object: divide
# 或：补丁里写了 `; pd quit;`，退出后 grep 不到 loadbang 的 print
```

## 触发条件

- 平台：OHOS aarch64，宿主 `puredata/0.54.1`，插件 `pd-maxlib 1.6.0` / `pd-mjlib 0.2.0`。
- 交付物是**宿主在运行时按类名 dlopen 的模块**（`<class>.pd_linux`），没有独立可执行入口。

## 根因分析（三个坑）

### 1. 宿主可能不在 PATH

运行时环境（`conanrun`）不保证 `pd` 在 PATH；必须用宿主依赖的**绝对路径**：

```python
pd_bin = os.path.join(self.dependencies["puredata"].package_folder, "bin", "pd")
```

### 2. 补丁内 `; pd quit;` 与 `loadbang` 输出竞争

`pd` 即使 `-nogui -nosound` 也是常驻事件循环。补丁里惯用的「加载后立刻 `; pd quit;`」
会与 `loadbang` 触发的对象输出（`print`）竞争：**个别 print 尚未写到 stdout，进程就退出**，
于是 `grep` 断言随机失败。

正确做法：**不在补丁内主动退出**，用外层 `timeout` 结束进程——输出在退出前已落地：

```sh
timeout 20 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open test.pd > log 2>&1 || true
```

本任务真机实测即因此把补丁改为只保留 `loadbang → 对象 → print <TAG>`，由 `timeout` 收尾。

### 3. 断言必须落在确定性类上

外部对象集合里大量类带随机/时基/环境行为。验收断言只选**纯函数**类，实测：

| 库 | 对象 | 输入 | 期望输出（print 标记） |
|----|------|------|------|
| pd-maxlib | `[divide]` | `10 20` | `MAXLIB_DIVIDE: 0.5` |
| pd-maxlib | `[plus]` | `3 4` | `MAXLIB_PLUS: 7` |
| pd-mjlib | `[n2m]` | note `C5` | `MJLIB_N2M: 72` |
| pd-mjlib | `[n2m]` | note `D#3` | `MJLIB_N2M: 51` |

## 解决方案

三步消费者测试（`test_package/conanfile.py` + `*.sh` + `*.pd`）：

1. 显式 `PD_BIN=<host_dep>/bin/pd`、`EXT_DIR=<pkg>/lib/pd-externals`，先断言目标
   `<class>.pd_linux` 存在；
2. 无头运行最小补丁：`"$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open patch.pd`，
   外层 `timeout 20`；
3. grep 确定性标记，全部命中才 rc=0。

### 示例

```sh
# 见 test_package/test_pd_maxlib.sh / test_pd_mjlib.sh
PD_BIN=<puredata>/bin/pd EXT_DIR=<pkg>/lib/pd-externals PATCH=test.pd
timeout 20 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > log 2>&1 || true
grep -q 'MAXLIB_DIVIDE: 0.5' log && grep -q 'MAXLIB_PLUS: 7' log
```

期望（真机 OHOS）：

```
MAXLIB_DIVIDE: 0.5
MAXLIB_PLUS: 7
MAXLIB_CHECK_SUMMARY fails=0
```

## 禁止做法（实测依据）

- ❌ 用裸名 `pd`：conanrun 不保证 PATH → `pd: command not found`。
- ❌ 补丁里 `; pd quit;` 后 grep：与 `loadbang` 输出竞争 → 随机少行、假失败。
- ❌ 断言随机/时基类：偶发失败，不能当验收判据。
- ❌ 用「链接一个消费者可执行文件」代替：插件没有可执行入口，必须由**真机宿主**加载。

## 通用性证据（独立第二库）

`pd-mjlib 0.2.0`（独立上游仓，Debian orig，sha256 `53d52bdf…29779`）用**同一套**
`test_pd_*.sh` 模式在真机验证：8 个 `.pd_linux`，`[n2m]` note `C5`→72、`D#3`→51，
`MJLIB_CHECK_SUMMARY fails=0`。两库消费者测试均通过。

## 查重反证（vs 已有条目）

- **E280**（Tcl `thread.test` hang / 子解释器不退出）：现象同属「测试进程不自行退出」，
  但根因与解法不同——E280 是 Tcl 线程回收，本稿是**宿主事件循环 + 补丁内退出的输出竞争**，
  解法是「不主动退出、用外部 timeout」，并新增「断言确定性类」「显式宿主绝对路径」两点。
- 关键词族 0 命中（main tip）：
  `grep -rilE 'pd_linux|-nogui.*pd|loadbang|; pd quit;' knowledge/{graph,doc,drafts}` → **0**。

## 证据（PR/分支/配方/日志）

- 分支 `feat/pd-maxlib-1.6.0` PR #13770；第二库 `feat/pd-mjlib-0.2.0` PR #13771。
- `test_package/test_pd_maxlib.sh` / `test_pd_mjlib.sh` / `test_pd_*.pd`。
- 真机 `conan create` `CREATE_RC=0`，消费者 maxlib 2/2、mjlib 2/2。

## 元信息

- authors: `frj__`（contributor_id: `frj__`）
- source_event: pd-maxlib 1.6.0 + pd-mjlib 0.2.0 消费者无头加载测试（2026-09-29）
- draft: true —— 待主编审核后 promote 为正式 E 条目
