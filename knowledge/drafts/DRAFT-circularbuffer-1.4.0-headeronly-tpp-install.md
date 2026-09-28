# DRAFT: header-only 库 .tpp/.ipp 实现文件必须随 .hpp 一起安装

- **来源库**: circularbuffer 1.4.0（rlogiacco/CircularBuffer，Arduino 风格环形缓冲模板库）
- **来源日期**: 2026-09-23
- **平台**: HarmonyOS PC (arm64, OHOS), clang 15 / libc++ / C++17

## 问题

header-only 模板库为可读性把模板/非模板实现拆分到 `.tpp` 文件，
主头文件（`CircularBuffer.hpp`）末尾以 `#include <CircularBuffer.tpp>`
引入。Conan 配方 `package()` 若只复制 `*.h`/`*.hpp`（常见 header-only
配方模板默认只含这两类），`.tpp` 不进 `include/` → 消费者（test_package
或下游）编译时主头展开 `#include <CircularBuffer.tpp>` 找不到文件。

## 根因

安装完整性错误：主头与实现分离文件未同时打包。与平台无关。
（区别于 graaf 的 .tpp 链接重复符号问题——那是 .tpp 内非 inline 自由
函数的多翻译单元 ODR 冲突，需标 inline，属于另一模式。）

## 方案

`package()` 中除 `*.h`/`*.hpp` 外，增加：

```python
from conan.tools.files import copy

def package(self):
    copy(self, "*.h",   src=self.source_folder, dst=self.package_folder + "/include")
    copy(self, "*.hpp", src=self.source_folder, dst=self.package_folder + "/include")
    copy(self, "*.tpp", src=self.source_folder, dst=self.package_folder + "/include")  # 关键
    copy(self, "LICENSE*", src=self.source_folder,
         dst=self.package_folder + "/licenses", keep_path=False)
```

`.ipp`/`.tcc`/`.inc` 等分离实现文件视上游包含方式同样处理。

## 验证

- 仅复制 `*.h`/`*.hpp` 时：`conan create` 的 test_package 编译阶段报
  `CircularBuffer.tpp file not found` 类错误。
- 增加 `*.tpp` 复制后：`conan create` 全流程通过，test_package
  `test_circularbuffer` 1/1 Passed（消费者通过已安装公开头调用
  push/shift/pop/unshift/first/last/size/available/isEmpty/isFull/clear/
  copyToArray/operator[]，退出码 0，产物为 OHOS arm64 ELF）。

## 适用边界

- 适用：所有 `.tpp`/`.ipp`/`.tcc` 分离实现的 header-only 库的 Conan 配方。
- 反例：单头分发库（如 doctest、Catch2 单头版）无分离实现文件，不适用；
  编译期才生成的实现（如模板实例化产物）不适用。
- 若上游 CMake 提供 install 目标，优先 `cmake.install()` 由上游统一安装。
