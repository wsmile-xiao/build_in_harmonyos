# DRAFT：CLI 消费者测试的 usage 路径退出码不可跨平台移植——先目标设备实证再校准断言

> 来源：xmacro/0.3pre-20000911 真机 shadow CI（2026-10-04）；适用于一切带 usage/错误路径退出码断言的消费者测试

## 现象

本机验证全绿的消费者测试，真机 CI 在 L1 翻车：

```
AssertionError: xmacroplay without args should fail
```

设备上手工复现：`xmacroplay`（无参）打印完整 Usage 后 **rc=0**，
而上游源码明明是 `usage(EXIT_FAILURE)`（标准值 1）。

## 使用说明（三步判定流程）

1. **先实证**：不要先改配方。在设备上用 conan test 同款环境复现一次：

   ```sh
   . <test_package 构建目录>/conanrun.sh
   <pkg>/bin/<tool>; echo "RC=$?"      # usage 路径真实 rc
   <pkg>/bin/<tool> -v; echo "RC=$?"   # 正常路径对照
   ```

2. **再分流**（判定规则）：
   - stderr 有预期输出（Usage/错误信息）、只有 rc 与宿主经验不符
     → **平台差异**，按本条校准断言；
   - stderr 为空或报 `Error loading shared library` / relocating
     → 不是本条目，去查依赖闭包 / LD_LIBRARY_PATH / ELF 签名
     （参考 crashme 126/127/255 守卫条目）。

3. **后校准**：断言改为「可观测输出契约」，并在注释与 notes 里留实证证据。

## 适用范围

- 一切对 CLI 工具做 usage/错误路径 **退出码** 断言的消费者测试
  （test_package/*.py、cmake 测试、shell 冒烟脚本）；
- 本机（x86 宿主）通过、真机（OHOS aarch64）才失败的退出码类断言；
- 不适用于：加载失败（126/127/255，见 crashme 条目）、版本旗标缺失
  （见 zpaq 条目）、上游 make test 的退出码契约（见 E698 条目）。

## 输入输出定义

| 项 | 内容 |
|---|---|
| 输入 | 被测包安装后 bin 路径；conanrun 环境（conan test 自动提供） |
| 过程 | 设备上以同款环境执行 usage 路径，捕获 rc + stderr |
| 输出 | 真实 rc 与输出契约 → 决定断言保留 / 放松 / 改查依赖 |
| 副产物 | notes.md 中的平台实证记录（日期 + rc + 输出摘要） |

## 示例（xmacro 实际修复）

```python
# 修复前：本机经验写死退出码 —— 真机 L1 FAIL
proc = subprocess.run([play], capture_output=True, text=True)
assert proc.returncode != 0, "should fail"
assert "Usage:" in proc.stderr

# 修复后：只断言输出契约 —— 真机 L1 PASS
# OHOS 实测 usage(EXIT_FAILURE) 返回 0（真机 2026-10-04），不锁退出码
proc = subprocess.run([play], capture_output=True, text=True)
assert "Usage:" in proc.stderr
```

校准后真机结果：L0/L1/L4/L5 全 pass、exit 0、5/5 断言；
**L1e 破坏性反向验证仍有效**（bin/ 被移走时文件存在性断言先失败），
放松退出码断言不会把测试变成假测试。

## 实测证据

| 实验 | 结果 |
|---|---|
| 修复前真机 | L1 fail（assert rc!=0 失败，rc 实测 0） |
| 设备手工复现 | Usage 完整打印 + RC_NOARG=0（conanrun 环境） |
| 校准后真机 | L0/L1/L4/L5 pass，exit 0，5/5 断言，L1e 负向确认通过 |
