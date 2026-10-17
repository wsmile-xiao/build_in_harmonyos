# E544 — GNU C 嵌套函数(gcc 扩展)在 clang 下报 "function definition is not allowed here"

## 错误特征

clang 编译含**函数体内嵌函数定义**（GNU C nested function，gcc 专有扩展）的 C 源码时报：

```
error: function definition is not allowed here
```

典型日志（libdumbtts 0.3.2 实测）：

```
In file included from libdumbtts.c:964:
./libdumbtts_dic.c:125:2: error: function definition is not allowed here
        {
./libdumbtts_re.c:302:2: error: function definition is not allowed here
        int chrget()
```

同一源码用 gcc 能编译（嵌套函数是 gcc 扩展），用 clang 从 2.0 起**从未实现**该特性，编译器把内层函数定义视为非法语法级错误。

## 触发条件

- 构建系统：任意（Makefile/CMake/autotools 均可触发）
- 阶段：compilation
- 编译器：clang 全版本（含 OHOS SDK clang 15）
- 源码特征：函数体内直接定义另一个函数，且该内层函数常**按引用捕获外层函数的局部变量**（修改会写回外层）。常见于 2000–2015 年编写的 C 代码（libdumbtts 0.3.2 编写于 2010 年，共 8 处嵌套函数）。

## 根因分析

GNU C nested function 是 gcc 的扩展特性：允许在函数体内定义函数，内层函数可以捕获并修改外层函数的局部变量（gcc 用 trampoline 实现）。clang 出于安全与实现复杂性从未支持此特性，遇到内层函数定义直接报 `error: function definition is not allowed here`（错误位置指向内层函数的 `{`）。

**关键语义陷阱**：嵌套函数对捕获的局部变量是**引用语义**——内层函数内对捕获变量的修改（如计数器 `wc=0`、游标 `c++`）会写回外层。因此提升为文件级函数时，捕获变量必须改为**指针参数**，不能传值，否则行为不一致。

## 解决方案

### 推荐方案：提升为文件级 static 函数 + 捕获变量显式传参

1. 将嵌套函数体整体移到外层函数之前（或文件作用域），加 `static` 前缀。
2. 外层函数的局部变量中，凡被嵌套函数**读或写**的，都加入函数参数；**被修改的必须传地址**（`wchar_t *wc`、`char **c`、`int *count`），只读的传值即可。
3. 同步修改函数体内全部调用点，传入对应实参（如 `chrget(str, &c, &wc)`）。
4. 用 clang 重新编译验证。

libdumbtts 0.3.2 实例（全部成功修复）：

| 外层函数 | 嵌套函数 | 捕获变量 | 提升后签名 |
|---|---|---|---|
| `roman()` | `nchar` / `gchar`（2 个） | `wc`, `oc`, `goc`, `str`, `len` | `roman_nchar(wc,oc,goc,str)` / `roman_gchar(&wc,oc,&goc,&str,&len)` |
| `dic_compare_word()` | `chrget`（1 个） | `wc`（写） | `chrget_dic(str,outstr,&wc)` |
| `do_recognize_item()` | `chrget/chrgot/nchar/chcom/cmwrd`（5 个） | `wnc`, `c`, `d` | `chrget_re(&wnc,&c)` 等 |

修复后编译、演示程序、conan-verify 全部通过。

### 禁止做法

- ❌ 试图找 clang 开启嵌套函数的编译开关/clang flag——**不存在**，这是特性缺失不是警告级别问题。
- ❌ 用 `-Wno-*` 抑制——无效且掩盖错误。
- ❌ 把捕获变量按值传入（不传地址）——嵌套函数改动会丢失，产生静默逻辑错误。

## 验证

```bash
# 编译验证（修复后）
clang -fPIC -o libdumbtts.o -c -Wall libdumbtts.c
# 期望：0 errors（仅剩无害的 K&R 隐式 int warning）

# 功能验证（库行为不变）
./demo en "hello world"    # 输出 Len=12 / hello world

# 完整流程
ohc-run.py conan-verify libdumbtts 0.3.2   # G1-G4 全通过
```

## 适用边界

- **适用**：任何旧版 C 项目使用 gcc 嵌套函数（函数体内定义函数、捕获局部变量）导致 clang 编译失败。
- **不适用**：函数体内只有普通代码块（`{ }` 作用域）而非函数定义的情况，不属于本模式。
- 若嵌套函数数量多或捕获变量多，提升工作量大但**机械可重复**；建议逐个函数处理并随时编译验证。

## 关联条目

- 相关：无既有条目直接覆盖（本次为首次入库）。