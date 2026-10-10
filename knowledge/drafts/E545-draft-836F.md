# E545 — C++ function definition repeats default arguments

## 错误特征
Clang reports that a default argument is specified again when compiling a function definition whose forward declaration already provides the same defaults. In YAHA this occurred on the `findAffineGapScore` template in `src/SW.cpp`.

## 触发条件
- 构建系统: Any C++ build system
- 阶段: Compilation

## 根因分析
A default argument can be introduced by only one declaration in a scope. Repeating it on the later definition is ill-formed and Clang rejects the source.

## 解决方案

### 推荐方案
Keep the default arguments on the forward declaration and remove them from the corresponding definition. This preserves call sites and conforms to C++ rules.

### 禁止做法
- Do not remove the defaults from the first declaration if existing callers rely on them.

## 验证
```bash
conan create archives/y/yaha/0.1.83 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 关联条目
- Related: none
