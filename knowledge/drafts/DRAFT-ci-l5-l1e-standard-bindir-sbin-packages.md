# DRAFT: application 包产物目录用 bin/ 而非上游的 sbin/——CI L5/L1e 门禁只认 bin/lib，产物放 sbin/ 会 L5=warn 且 L1e 被跳过

## 基本信息

- 来源：sysrqd/17 真机 shadow CI r2→r3（2026-10-01）
- 阶段：packaging / CI gate（L5 产物存在性、L1e 破坏性反向验证）
- 严重度：2

## 错误特征

产物目录用 `sbin/`（上游 Makefile 安装到 `/usr/sbin` 的守护进程类包常见）时：

```
[warn] L5: No bin/ or lib/ content found
L5_RESULT=warn: no artifacts found
[step] L1e: Destructive negative test (R34)...
        [skip] L1e: No standard artifact dirs found to sabotage
```

conan create 本身成功、test_package 6/6 PASS、总 exit 0——但 L5 只看
`bin/`/`lib/`，产物在 `sbin/` 被视为「无产物」；更关键的是 **L1e 破坏性
反向验证被静默跳过**，包是否真依赖产物没有得到 CI 级证明。

## 根因分析

`build_and_test.sh` 的 L5（产物存在性）与 L1e（sabotage 破坏目录）都只扫描
Conan 标准目录 `bin/` 和 `lib/`。上游惯例安装到 `/usr/sbin` 的包（sysrqd、
NUT upsd、kmod 等）如果照搬上游布局打包到 `sbin/`，CI 无法识别产物，L5 永远
warn、L1e 永远 skip——这两项都不是 fail，容易被当成「过了」，但 L1e 缺失违背
「test_package 必须真链接被测包」的门禁意图（对比 E560：bin/ 被移走仍通过才判
空壳；根本不给 sabotage 机会等于绕过了该检查）。

## 推荐方案

**方法**：package-to-conan-standard-bindir

- `package()` 把可执行文件复制到 `bin/`（并在配方注释说明上游原生路径差异）；
- `package_info()` 用 `self.cpp_info.bindirs = ["bin"]`；
- test_package 的兜底路径相应用 `../bin/<name>`。

```python
copy(self, "sysrqd", src=src, dst=os.path.join(self.package_folder, "bin"))
os.chmod(os.path.join(self.package_folder, "bin", "sysrqd"), 0o755)
self.cpp_info.bindirs = ["bin"]
```

改后效果（sysrqd r3 实测）：

```
L5_RESULT=pass: bin/ has content
[ok] L1e: Negative test confirmed — test genuinely depends on sysrqd
```

注意连带影响：产物进 `bin/` 后 L2 冒烟会执行 `--version/--help`——无参数解析
的 CLI（main(void)）会 non-blocking skip/fail，按 E503 处理并在 notes 归因，
不要为 L2 伪造参数解析。

## 验证证据

sysrqd/17：r2 sbin/ → L5=warn + L1e=skip；仅把产物目录改为 bin/ 后 r3 同日
复跑 → L5=pass + L1e genuine（`[sabotage] bin/ moved away` → 测试 FAIL），
总 exit 0。

---
Status: UNMATCHED
