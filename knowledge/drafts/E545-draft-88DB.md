# E545 — test_package 硬编码构建机个人绝对路径：目标 worker 缺少该路径时 `set -e` 直接中止整个 test_package

## 错误特征

```
stat: cannot statx '/storage/Users/currentUser/.harmonybrew': No such file or directory
```

或（GNU coreutils 写法）：

```
stat: cannot stat '/storage/Users/currentUser/.harmonybrew': No such file or directory
```

出现在 `conan create` / `conan test` 的 `test_package` 阶段尾部，且脚本以 `set -e` 运行 → 整条测试链在该行中止，`conan create` 返回非 0。典型上下文：该行是"遮蔽宿主前缀根"的校验层（如 `chmod 000 "$HOME/.harmonybrew"` 前先 `stat` 确认存在）。

## 触发条件

- 构建系统: conan（v2 recipe + `test_package/run_test.sh` 或等价 shell 钩子）
- 阶段: testing（`conan create` → `test_package`）
- 环境差异: 编写配方的机器上存在某个人目录（`~/.harmonybrew`、`~/.conan2`、`/storage/Users/<user>/...`），目标 CI worker 上不存在

## 根因分析

包作者在自测时以"宿主缓存/前缀遮蔽"为目的写了一条**存在性前置检查**，并把构建机的个人绝对路径当作必然存在的对象：

```sh
stat -c %a /storage/Users/currentUser/.harmonybrew   # 写作者机器上必然存在
chmod 000 /storage/Users/currentUser/.harmonybrew
```

这类校验本身是合理的负向控制（证明被测包没有回落到宿主缓存），但它**不是被测包的性质，而是构建机的性质**：

- `set -e` 下，`stat` 失败即整条 `run_test.sh` 中止 → `test_package` 失败 → `conan create` 失败；
- 该失败与配方/产物质量无关（源码编译、安装、其余断言全部通过），却**硬性阻断 CI 与发布**；
- 由于失败点在测试收尾，日志尾部才有报错，容易被误判为"偶发环境问题"而反复重跑。

真实案例：`r-base/4.5.1` 于 2026-08-11 合入官方基线，但因其 `test_package/run_test.sh` 硬编码 `/storage/Users/currentUser/.harmonybrew`，在缺少该目录的机器上必然失败，**两个月未能发布到制品仓**，直接阻塞依赖它的 R 生态下游包（`rmatrix`/Matrix 1.7-5 因此止损 `dependency_missing`）。

## 解决方案

### 推荐方案

把**可选的**宿主遮蔽层改为"根实际存在才执行"，并在跳过时显式打印状态、不改变退出码：

```sh
host_root="$HOME/.harmonybrew"      # 或任何与构建机绑定的个人路径
host_mask=0
if [ -e "$host_root" ]; then
    chmod 000 "$host_root"
    host_mask=1
fi
...
# 收尾恢复同样以 $host_mask 判定
if [ "$host_mask" = "1" ]; then
    chmod 755 "$host_root"
    echo "HOST_MASK=PASS"
else
    echo "HOST_MASK=SKIPPED (root absent: $host_root)"
fi
```

关键点：

1. **必须保留无条件校验层**：真正证明"未回落宿主缓存"的主层（如遮蔽 `~/.conan2` / conan cache）保持无条件执行，负向控制强度不降级；被降级的只是与个人目录绑定的第二层。
2. **跳过要可观测**：打印 `SKIPPED` 而不是静默 `|| true`，避免"静默跳过"伪装成"已通过"。
3. **CI 侧不要在目标机预置该目录来"消错"**：那只是把失败隐藏起来，包的发布仍会依赖不可复现的宿主状态。

## 验证

```bash
# 1) 静态排查：test_package 中出现构建机个人路径即高危
grep -nE '/storage/Users/|[.]conan2|[$]HOME/[.]harmonybrew' <pkg>/test_package/*.sh

# 2) 动态复现：在"缺少该根"的环境下跑（可用临时 HOME 模拟）
HOME=$(mktemp -d) conan create <pkg> -pr:h=<profile> -pr:b=<profile> --build=missing
# 期望：不再出现 stat/cannot statx 中止；输出 HOST_MASK=SKIPPED (root absent: ...) 且退出码 0
```

## 关联条目

- 相关: E316（Conan 包被移动到新路径后 NEEDED 解析失败 —— 同属"宿主/绝对路径假设"，但 E316 是产物侧，本条是测试脚本侧）、E317（install sed 范围限定，同属"可重定位性"）
