# DRAFT: 上游自写测试框架 CWD 数据文件缺失静默空转通过 + 负向编译断言缺口（immutable 复合赋值）的识别与修复（exprtk 0.0.3 R01→R02 闭环）

## 问题 1：CWD 数据文件缺失 → 静默 return true（空转通过）

上游**自写测试框架**（非 GoogleTest/Catch2 等外部框架）常以**进程 CWD 相对路径**
加载数据文件。exprtk 0.0.3 的 `exprtk_test.cpp` 中 `load_expressions()` 对缺失文件
返回 0 条，上游 `run_test14()` 随后执行：

```cpp
if (expr_str_list.empty())
{
   return true;   // 数据文件缺失 → 静默通过，实际评估 0 条表达式
}
```

测试打印 `SUCCESS`，但实际**空转**——这是假阳性。exprtk 0.0.2 首轮 W4 审计曾以
P0 捕获（run_test14 仅 0.006s），0.0.3 R01 双版本复现确认同机理。

### 实测证据（exprtk 0.0.3）

- 数据文件：`exprtk_functional_test.txt` + `exprtk_functional_ext_test.txt`
  （0.0.3 tarball 内含；`exprtk_noncommutative_test.txt` 官方全版本无此文件，
  `git rev-list --all --objects` 零命中，见 run14_datafile_audit.log）
- 数据文件不在进程 CWD：run_test14 空转通过（毫秒级）
- 数据文件在进程 CWD：run_test14 真实加载、真实评估并 SUCCESS（69.1s）

## 问题 2：负向编译断言缺口（immutable 符号复合赋值）—— R02 已修复

上游 `run_test21()` 用"期望编译失败"的负向断言验证 immutable 符号表约束：

```cpp
std::make_pair<std::string,bool>("z := y + x - w"   , false),  // := 触发 ERR268，拒绝 ✓
std::make_pair<std::string,bool>("z == (w += y / x)", false)   // += 复合赋值，R01 接受 ✗
```

R01 最小复现（repro21.cpp）确认：`z := y + x - w` → ERR268（正确拒绝）；
`z == (w += y / x)` → 编译成功且 w 被真实修改（w_after=6.4）——测试 FAILED。

### 根因（R02 定位）

`exprtk.hpp` 的 `interval_container_t::add_interval` 用`in_interval(end)` 判重叠：
half-open 策略 `is_within(v,begin,end)=(begin<=v && v<end)` 把**相邻** immutable
变量区间（栈上相邻：w=[d8,e0)、z=[e0,e8)）的**共享边界点 e0** 判为与 z 区间冲突，
`add_interval(d8,e0)` 拒绝登记 → w 区间不在 immutable map → `z == (w += y / x)`
中 `assign_immutable_symbol(w)` 落空 → 复合赋值静默通过。

复现路径：`parse_symtab_symbol` 两个符号都调用了 `lodge_immutable_symbol`（诊断
确认），但 map 只剩 1 个区间（诊断 interval_count=1 且为 z 的区间）。

### R02 修复（真重叠检测）

```cpp
// add_interval：仅当 begin<eend && ebegin<end（真重叠）才拒绝；相邻区间共享边界合法
if (end <= begin) { return false; }
for (itr...) {
   if ((begin < eend) && (ebegin < end)) { return false; }
}
interval_map_[end] = {begin, end};
```

- 补丁：配方 `patches/0001-exprtk.hpp.patch`（纯 unified diff，refresh-patch 命名）
- 复验：repro21b 修复后 `z == (w += y / x)` → ERR268；`w += y / x`、`w := y + x`、
  `z := w` 均 ERR268；`z = w + 1` 正常（读不受限）
- 全量：23/23 SUCCESS（upstream_full_run_r02.log，run_test21 0.4s 通过）

## 根因（问题 1）

上游自写测试框架对数据文件缺失无失败路径（空列表直接 return true），
测试垄断了"通过"信号但未做真实工作。

## 修复与验证

1. 复制数据文件到测试执行目录（conan build() 中
   `copy(self, "exprtk_functional*_test.txt", source_folder, build_folder)`），
   运行后**核对各用例耗时**——空转毫秒级、真实执行数百秒，耗时是识别空转第一信号。
2. 对负向断言失败写**最小复现**独立确认归属；定位到区间容器边界误判时以
   **真重叠检测补丁**修复（与 `:=` ERR268 行为一致），修复后全量重跑 + repro21 复验。
3. 数据文件清单进 MANIFEST.yml 的 `upstream_check_command`；缺失文件显式处理预期。

## 适用边界

- 适用：①任何上游自写测试框架从 CWD 相对路径加载数据、缺失静默通过；
  ②任何使用 half-open 区间容器做内存区间登记（immutable 保护）的解析器——
  相邻区间共享边界点误判会静默丢弃后登记区间、保护失效。
- 反例/不适用：外部测试框架（GTest/CTest）自带失败路径；配方/平台可修问题不适用
  "归因上游"结论（须先最小复现排除平台影响）。

## 查重差异

- 与 E379（ITK ExternalData 下载闭包）differentiator：E379 解决下载闭包，本条目
  解决 CWD 静态加载空转识别 + 相邻区间边界误判修复。
- 与 E370（Meson fixture 统计）differentiator：E370 管平台条件 fixture 计数。
- 新增差异：R01→R02 闭环证据（22/23 → 23/23）；"耗时核对识别空转"；"最小复现
  归因负向断言缺口 → 真重叠检测补丁"组合方法。add_interval/interval_container
  模式四范围查重零命中（无既有 E 条目/草稿覆盖该区间容器机理）。

## 关系

- similar_to: E379（测试输入闭包）、E370（上游测试完整性）
- conflicts_with: 无
- verification_cmd: `cp exprtk_functional*_test.txt <exec_dir> && ./exprtk_test`；
  `clang++ repro21.cpp && ./a.out`（修复前后对比）；全量 23/23 日志
  upstream_full_run_r02.log（sha256=5210c3e4c35af16b1de245e89e657b6b41f382d62791a6b473318da9fe446ee5）