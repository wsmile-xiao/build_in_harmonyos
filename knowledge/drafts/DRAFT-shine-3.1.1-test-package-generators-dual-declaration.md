# shine 3.1.1 — Conan 2 test_package 生成器不能"属性 + generate()"双写 (draft)

**Category**: conan | testing · **Severity**: 2 · **Tool**: conan create

## 症状

`conan create` 的 test_package 阶段报：

```
ERROR: Error in generate() method, line 14
  CMakeDeps(self).generate()
  ConanException: CMakeDeps is declared in the generators attribute, but was
  instantiated in the generate() method too. It should only be present in one of them.
```

## 根因

Conan 2 对同一 generator 在类属性 `generators` 与 `generate()` 方法内各声明一次的
写法直接抛异常（Conan 1 允许）。模板/脚手架生成的 test_package 常双写：类属性
带 `CMakeDeps, CMakeToolchain`，generate() 里又显式 `CMakeDeps(self).generate()`。

## 处置（可复用）

二选一，推荐与仓库既有成功 test_package（a52dec/0.7.4）一致：类属性只放
`VirtualRunEnv`（供 `env="conanrun"`），`CMakeDeps/CMakeToolchain` 只在
generate() 内显式实例化；test() 用 `self.run("./test_shine", env="conanrun")`
（同时满足 CI L0d 门禁，见 E472）。

```python
generators = "VirtualRunEnv"
test_type = "explicit"

def generate(self):
    CMakeDeps(self).generate()
    CMakeToolchain(self).generate()

def build(self):
    cmake = CMake(self); cmake.configure(); cmake.build()

def test(self):
    self.run("./test_shine", env="conanrun")
```

## 验证

- 修复前：G2 test_package generate() 报 ConanException 失败。
- 修复后：conan-verify shine 3.1.1 G2 PASS；test_package 消费者测试执行通过；
  finish W3 L0/L1 PASS。

## 适用边界

- 生效：Conan 2 的 test_package/consumer 配方。
- 反例：Conan 1 无此限制；只用 generators 属性、不写 generate() 的配方不受影响。
- 关联：E472（test_package self.run L0d 门禁）、E298（VirtualRunEnv 运行环境）。