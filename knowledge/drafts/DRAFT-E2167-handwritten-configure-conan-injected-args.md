# E2167: 手写 configure 拒绝 Conan AutotoolsToolchain 注入的标准目录参数（Unknown option）

## 问题描述

ck 0.7.2 适配 OHOS PC 时，`conan create` 的 configure 阶段直接失败：上游 `configure` 是作者手写的脚本（非 autoconf 生成），Conan 2.x 的 `AutotoolsToolchain` 默认注入 `--prefix --bindir --sbindir --libdir --includedir --oldincludedir --datarootdir` 等标准 GNU 目录参数，手写脚本的参数白名单不含 `--oldincludedir`，直接以 `Unknown option` 退出（稳定错误签名）。

## 根因

- 手写 configure 用 case/白名单校验参数，不认识的选项即致命退出（不同于 autoconf configure 的宽容语义）；
- Conan 2.x 工具链无条件注入全部标准目录参数，其中 `--oldincludedir` 最少被上游脚本收录。

## 解决方案

配方 `generate()` 中用 Conan 官方 API 剪除（不要为此打补丁，也不要手写过滤器）：

```python
def generate(self):
    tc = AutotoolsToolchain(self)
    tc.update_configure_args({"--oldincludedir": None})
    tc.generate()
```

同一手写 configure 的平台识别问题（`uname -s` 白名单无 HarmonyOS）是**另一个独立问题**，用 E160 类平台补丁解决，两类补丁分开提交、分开申报。

## 验证

- `conan create .` configure 阶段无 `Unknown option`，顺利进入编译；
- 配方 diff 中不因本问题出现 configure 补丁。

## 适用范围

- ck、lzip 家族、sqlite 等一切手写 configure 的上游；
- 反例：autoconf 生成的 configure 认识全部标准目录参数，无需此处理；
- 解除条件：上游将来收录该参数或改用 autoconf。

## 风险与边界

- `update_configure_args` 逐参数处理即可，不需要清空全部注入；
- 若同时需要平台映射补丁，两个补丁语义独立，`patch_classification` 中分别标注。
