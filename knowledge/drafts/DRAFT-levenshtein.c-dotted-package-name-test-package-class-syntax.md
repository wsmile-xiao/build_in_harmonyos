# DRAFT — 点号包名 → conan-init test_package 类名 SyntaxError（levenshtein.c 2.0.2）

## 问题

包名含点号的 C 库（如 `levenshtein.c`）经 `ohc-run.py conan-init` 生成配方后，
`test_package/conanfile.py` 的类名会带点号（`class Levenshtein.CTestConan(ConanFile):`），
Python 标识符不允许 `.`，`conan create` 加载 test_package 时必然抛：

```
ERROR: Error loading conanfile at '.../test_package/conanfile.py': Unable to load conanfile
  File ".../test_package/conanfile.py", line 15
    class Levenshtein.CTestConan(ConanFile):
                     ^
SyntaxError: invalid syntax
```

## 根因

conan-init 的配方模板用包名做类名占位（`{NAME}TestConan` / `{Name}`），包名中的 `.`
被原样带入 Python 类名。Python 类名只能是合法标识符（字母/下划线开头，无 `.`），
因此任何包名含点号的库生成 test_package 后都无法被 conan create 加载。
G2 表现为 "conan create 失败"，首错是 test_package 的 SyntaxError，与配方 build()/package()
本身无关。

## 方案

手动把 `test_package/conanfile.py` 的类名去掉点号（保持可读语义即可）：

```python
# 修复前（conan-init 生成，SyntaxError）
class Levenshtein.CTestConan(ConanFile):

# 修复后
class LevenshteinCTestConan(ConanFile):
```

然后重跑 `ohc-run.py conan-verify <name> <ver>`，G2 conan create 必须能加载
test_package 并运行消费者用例。

## 验证

- levenshtein.c 2.0.2：类名改为 `LevenshteinCTestConan` 后，conan-verify G2 PASS；
  test_package 消费者用例 1/1 运行通过（`reports/conan-create.log`）。
- 该修复只改 test_package 类名，不影响配方 build()/package()/package_info()。

## 适用边界

- 适用：包名含点号的 C/C++ 三方库（如 `x.y` 命名的单文件库），conan-init 生成
  test_package 后必须核验并修正类名。
- 边界：包名不含点号的库不触发；E478 是"版本号含点号致 conan-verify G4 正则不匹配"
  的另一个点号问题（阶段不同：G4 产物校验 vs test_package 加载），勿混用。
- 反例：改包名/版本号绕开点号属于伪修复，应修类名而非改名。

## 查重差异

- 与 E478（dotted version，conan-verify G4 package ID 正则）触发阶段不同、修复面不同。
- 与 DRAFT-commander-1.4.0（裸 Makefile 配方 build/package 陷阱，含
  `compiler_executables:c` conf）无重叠：本条目针对 test_package 模板类名语法。
