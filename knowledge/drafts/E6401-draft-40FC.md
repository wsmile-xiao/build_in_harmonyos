# E6401 — CMake find_program(clang-tidy) 多行参数生成坏 build.make（missing separator）；Conan 配方须用 cache_variables 禁用 clang-tidy

## 错误特征

配置成功但 make 一启动即停止：

```
CMakeFiles/smtpclient.dir/build.make:82: *** missing separator.  Stop.
make[1]: *** [CMakeFiles/Makefile2:87: CMakeFiles/smtpclient.dir/all] Error 2
```

同一文件的 build.make 中可见注入的多行 clang-tidy 参数：

```
$(CMAKE_COMMAND) -E __run_co_compile --tidy="/data/service/hnp/bin/clang-tidy;-header-filter=.;
    -line-filter=[...];
    -checks=*, ...
```

## 触发条件

- 构建系统：CMake + Unix Makefiles 生成器
- 阶段：configuration 成功、compilation 立即失败
- 前提：环境中安装了 clang-tidy（find_program 找到）+ 上游 CMakeLists 把多行 clang-tidy 参数写入 `--tidy`（如 cpp-smtpclient-library 1.1.14）
- 工具链：OHOS clang 15 / 任意 clang + clang-tidy

## 根因分析

上游 `find_program(CLANG_TIDY_EXE NAMES "clang-tidy")` 找到 clang-tidy 后，把含换行、分号、逗号的整段 `--tidy` 参数（header-filter、checks 列表、line-filter）作为 CXX_CLANG_TIDY target 属性。CMake 生成 build.make 时把该多行字符串原样展开进配方行，换行后未以 tab 起始的续行被 make 解析为 "missing separator"。

关键陷阱：Conan 配方 `tc.variables["CLANG_TIDY_EXE"] = "..."` **无效** —— CMake 的 `find_program` 优先读取 cache 变量，toolchain 文件里以普通 variables 写入的值不进入 cache，find_program 仍会重新探测到 clang-tidy。必须用 `tc.cache_variables`。

## 修复方案

Conan 配方 `generate()`：

```python
def generate(self):
    tc = CMakeToolchain(self)
    # find_program 优先读 cache；variables 无效，必须 cache_variables
    tc.cache_variables["CLANG_TIDY_EXE"] = "CLANG_TIDY_EXE-NOTFOUND"
    tc.generate()
```

无 Conan 时：`cmake .. -DCLANG_TIDY_EXE=CLANG_TIDY_EXE-NOTFOUND`

clang-tidy 是静态检查工具，非构建必需；禁用不改变产物，`-Werror -pedantic-errors` 等编译期告警不受影响。

## 验证

```
grep -c 'clang-tidy' <build>/CMakeFiles/<tgt>.dir/build.make   # 修复后 = 0
make -j1                                                        # 通过
```

实测（cpp-smtpclient-library 1.1.14）：本地首次 make 报 missing separator；改用
`tc.cache_variables["CLANG_TIDY_EXE"]="CLANG_TIDY_EXE-NOTFOUND"` 后 conan-verify
G0-G4 全部 PASS，上游 642/642 测试通过。

## 适用边界与反例

- 适用：上游 CMakeLists 用 `find_program(clang-tidy)` + 多行 `--tidy` 参数（header-filter/checks 列表跨行）的库；安装了 clang-tidy 的环境。
- 反例/不适用：未安装 clang-tidy 的环境不会触发（find_program 找不到，跳过）；上游用单行 `-DCMAKE_CXX_CLANG_TIDY` 或自定义 target 的不受影响。
- 与 E6341（X11 imake 的 cpp 塌缩制表符致 missing separator）症状相同但根因、修复完全不同：E6341 是 imake 体系 + FIXUP_CPP_WHITESPACE，本条是 CMake build.make + cache_variables 禁用 clang-tidy。

## 查重差异

- `knowledge/graph/` 正式条目：无命中（检索 "clang-tidy"、"missing separator" 无相关 E 编号）
- `knowledge/doc/`：无命中
- `knowledge/drafts/`：E6341-draft-2725 命中 "missing separator" 关键词，但为 X11 imake 场景（trigger_overlap），根因（cpp 塌缩制表符 vs clang-tidy 多行参数）、方案（imake KludgeOutputLine 补丁 vs cache_variables 禁用）、适用边界均不同 → 非完整重复，新增差异成立
- 结论：`new_draft`，走路径 B（知识库扩展）
