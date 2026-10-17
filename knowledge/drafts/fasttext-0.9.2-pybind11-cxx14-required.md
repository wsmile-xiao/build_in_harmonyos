# fasttext 0.9.2：pybind11 3.x 头文件要求 C++14（`-std=c++11` 编译失败）

> 草稿（DRAFT）— 来自 fasttext 0.9.2 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 `knowledge/drafts/fasttext-0.9.2-pybind11-cxx14-required.kv`

## 软件与平台

- **软件**：fasttext 0.9.2 的 Python 绑定（fasttext_pybind，pybind11 3.1.0）
- **平台**：HarmonyOS PC aarch64，clang 15.0.4，python 3.12.9，numpy 1.26.4

## 现象

`setup.py build_ext --inplace` 失败，`-std=c++11` 下 pybind11 3.1.0 头文件编译报
6 个模板错误：

```
pybind11/include/pybind11/detail/common.h ... struct overload_cast { ^
note: candidate constructor (the implicit move constructor) not viable:
      requires 1 argument, but 2 were provided
6 errors generated.
```

## 根因

pybind11 **3.x 的最低语言标准是 C++14**（3.0 起放弃 C++11）。fasttext 的
`setup.py` 用 `has_flag()`/`cpp_flag()` 探测 C++14/C++11 后追加 `-std=...`，
但 distutils 编译器可执行名被解析为不存在的 `cc`，探测全部失败回退 RuntimeError；
修复探测后按旧逻辑优先生成 `-std=c++11`，于是 pybind11 头文件编译失败。
OHOS 的 clang 15 默认 gnu++14 本可满足，显式 `-std=c++11` 反而绕过了默认值。

## 方案

在 Extension 的 `extra_compile_args` 显式使用 `-std=c++14`（clang 15 恒支持），
并确保构建脚本不因编译器探测（缺 `cc`）而误判。fasttext 采用固定
`return '-std=c++14'` 跳过探测（补丁 0004）。

## 验证

- `setup.py build_ext`（CC/CXX 指向 /data/service/hnp/bin/clang++）成功产出
  `fasttext_pybind.cpython-312-aarch64-linux-ohos.so`
- `import fasttext_pybind` OK；上游单元测试 83/83 通过
- `-std=c++11` 时 6 个模板错误可复现并消失

## 查重与差异

- **similar_to**：`DRAFT-pybind11-3.1.0-test-cxx20-rebuild` —— 该条是测试模块未显式
  `-std` 时默认 gnu++14 的 SKIPPED 主题；本条是**构建侧显式 `-std=c++11` 必须提升
  到 C++14** 的主题，方向互补、不重复。
- 正式条目无覆盖（E458 为 restinio C++14 header-only，主题不同）。

## 适用边界

- 适用：任何用 pybind11 3.x（含 3.0+）构建 Python 绑定的 OHOS/Linux 包；
  含带 `-std=c++11` 的 setup.py/CMake 显式标志的库。
- 反例：pybind11 2.x 仍支持 C++11，不必提升；若构建系统默认标准已 ≥C++14 且未显式
  传 `-std=c++11`，无需改动。