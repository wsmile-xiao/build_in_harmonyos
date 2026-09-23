# E560 — CLI 工具 --help 按设计返回非零退出码，test_package 需检查输出而非退出码

## 错误特征

test_package 里用 `self.run()` 探测 CLI 二进制的版本/帮助信息，被测二进制
明明能正常打印帮助，Conan 却直接判失败：

```
ERROR: fdkaac/1.0.9 (test package): Error in test() method, line 42
        self.run(f"{fdkaac} --help", env="conanrun")
        ConanException: Error 1 while executing

$ fdkaac --version
fdkaac: unrecognized option: version
```

手动运行同一命令，帮助横幅（首行含版本号）打印完全正常，只是退出码为 1。

## 触发条件

- 构建系统: 任意（Conan test_package）
- 阶段: testing —— 仅当被测产物是 CLI 可执行文件、且上游把 -h/--help 实现为
  「打印横幅后非零退出」时发生
- 高发对象: 老式 C CLI 工具。fdkaac 1.0.9 `src/main.c` 即此写法：
  `--version` 直接 unrecognized option（上游没有该选项）；
  `--help` 打印横幅后 `return usage(), -1;`，退出码 1

## 根因分析

上游 CLI 约定与 Conan 测试约定的语义错配，不是 OHOS 平台问题：

- 上游约定：usage() 打印帮助并 `return -1`，非零退出码表示「没有执行实际工作」。
- Conan 约定：`self.run()` 默认把非零退出码当失败抛 ConanException。
- 两者叠加：「帮助能正常打印」的二进制被误判为测试失败；
  换 `--version` 探测又撞上「上游根本没有该选项」。

## 解决方案

### 推荐方案：断言输出内容，不依赖退出码

捕获 stdout+stderr 后断言版本横幅文本存在，退出码交给 `|| true` 吞掉：

```sh
# test_package/test.sh（fdkaac 1.0.9 实际交付写法，30/30 通过）
banner=$("$FDKAAC" --help 2>&1 || true)
echo "$banner" | head -1
case "$banner" in
    "fdkaac 1.0.9"*) echo "PASS: version banner OK" ;;
    *) echo "FAIL: unexpected banner: $(echo "$banner" | head -1)"; exit 1 ;;
esac
```

Python 侧等价写法：

```python
proc = subprocess.run([fdkaac, "--help"], capture_output=True, text=True)
assert "fdkaac 1.0.9" in proc.stdout + proc.stderr
```

### 回退方案：跳过版本探测，用真实工作验证

不探测 `--help`/`--version`，直接让二进制做一次真实编码并断言产物特征字节
（M4A 的 `ftyp` box、ADTS 的 `ff f*` 同步字），既避开退出码语义又满足
R34 实质测试：

```sh
"$FDKAAC" -b 128000 --silent -o out.m4a in.wav
head -c 12 out.m4a | od -An -c | grep -q ftyp    # M4A 容器
```

### 禁止做法

- ❌ `self.run(..., ignore_errors=True)` 之后不做任何输出断言 —— 等于空壳测试，
  CI L1e 破坏性反向验证（移走 bin/ 仍通过）会拦截，PR 被拒。
- ❌ 为让 `--help` 退出码变 0 而补丁上游 `src/main.c` 的 `return -1` ——
  上游行为是文档化设计，改它属于过度适配，徒增维护负担。

## 验证

```sh
# 1) 确认上游 --help 语义：横幅正常、退出码为 1
fdkaac --help; echo $?           # → 1
fdkaac --help | head -1          # → fdkaac 1.0.9 ...
# 2) grep 上游源码确认设计意图
grep -n "case 'h'" src/main.c    # → return usage(), -1;
```

## 关联条目

- 相关: E239（多用例 test_package 保留完整诊断 —— 同为 test_package 语义坑）、
  E298（Conan test_package 的显式运行与环境）、
  E325（OHOS 上先解析可用 shell 再跑测试脚本）
- 适用铁律: R34（test 必须实质依赖被测包 —— 本条给出 CLI 工具的实质断言写法）

## 来源

- 软件/版本: fdk-aac-encoder/1.0.9（`archives/f/fdk-aac-encoder/1.0.9`）
- 上游: https://github.com/nu774/fdkaac `src/main.c`
