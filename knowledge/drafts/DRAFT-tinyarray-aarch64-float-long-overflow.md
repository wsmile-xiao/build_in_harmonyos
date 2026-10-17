# AArch64 有符号整数浮点溢出检测不应依赖越界强转结果

> 路径 B 知识草稿，等待知识库维护者审核。对应 `.kv` 文件：`DRAFT-tinyarray-aarch64-float-long-overflow.kv`。
> 对应知识库扩展标题：`【知识库扩展】feat(tinyarray): 1.2.5 适配 HarmonyOS PC`

## 问题

64 位有符号 `long` 的最大值是 `2^63-1`，但 IEEE-754 `double` 无法精确表示它；转换后会舍入到 `2^63`。如果代码把浮点输入直接转成 `long`，再用结果符号判断是否溢出，检测逻辑就依赖了超范围浮点到整数转换的架构行为。

tinyarray 1.2.5 的上游转换器用 `numeric_limits<long>::max()` 作为浮点上界，并在强转后检查符号。对 `float(2**63)`，AArch64 的越界结果可饱和到 `LONG_MAX`，于是输入没有大于舍入后的上界、结果也不是负数，原逻辑不抛 `OverflowError`。Debian bug #1146590 报告了这一 ARM64 失败，并提供了比较精确 2 的幂边界的修复。

## 可复用处理

先在浮点域里判定输入是否位于目标整数范围，再执行整数强转。对于 64 位有符号 `long`，上界用可精确表示的 `2^63` 开区间；下界需要根据浮点类型能否表示 `-2^63-1` 来选择严格或非严格比较。只有边界检查通过后才调用 `static_cast<long>`。

不要用“强转后结果为负/正”识别浮点溢出，也不要把 `LONG_MAX` 转成 `double` 后当作精确上界。

## 回归验证

```python
tinyarray.array(float(2**63), int)       # 必须抛 OverflowError
tinyarray.array(float(-(2**63)), int)    # 必须成功
```

HarmonyOS PC aarch64、clang 15、CPython 3.14.7 实测：`conan create` 成功，consumer 断言 7/7 通过，其中覆盖有符号 long 的正负溢出边界和有效范围内值。上游完整 pytest 套件需要 pytest 与 NumPy；该真机环境未安装二者，因此本次未运行完整套件，也未将它们加入 tinyarray 运行时依赖。

## 适用边界

适用于将有限浮点数转为有符号整数，并尝试自行检测越界的 C/C++ 数值库、Python C 扩展和语言绑定。NaN 转整数属于另一类未定义行为，可参考草稿 E555；本条针对有限但超出整数范围的值。
