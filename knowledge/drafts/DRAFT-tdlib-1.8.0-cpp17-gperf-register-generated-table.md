# DRAFT: conan profile cppstd=17 与构建期生成器的旧方言代码冲突（gperf register）

> Draft: DRAFT-tdlib-1.8.0-cpp17-gperf-register-generated-table
> 来源：tdlib/1.8.0 适配（CMake + gperf 生成 MIME 表），2026-09-24
> 复用面：任何「构建期用 gperf / lex / bison / 自制生成器产出 C++ 源码」+ conan profile 固定 cppstd 的包

## 现象（真实首次错误）

```
$ make -j20          # ohos-aarch64 profile（compiler.cppstd=17）
auto/mime_type_to_extension.gperf:47:20: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]
gperf_case_strcmp (register const char *s1, register const char *s2)
                   ^~~~~~~~~
... 9 errors generated.
make[2]: *** [tdutils/CMakeFiles/tdutils.dir/build.make:527: .../mime_type_to_extension.cpp.obj] Error 1
make: *** [Makefile:146: all] Error 2          # exit=2
```

## 根因链

1. tdlib 自加 `-std=c++14`（`CMake/TdSetUpCompiler.cmake`），并只抑制了 C++14 时代的
   `-Wdeprecated-register`（该开关在 C++17 下不覆盖 `-Wregister`）。
2. conan profile 固定 `compiler.cppstd=17` → `CMakeToolchain` 生成
   `set(CMAKE_CXX_STANDARD 17)`；**CMake 把标准开关放在编译命令最后一位**，覆盖工程自己
   追加的 `-std=c++14`。
3. 实测（`compile_commands.json`）同一 TU 出现两条标准开关，后者生效：

```
/data/service/hnp/bin/clang++ ... -std=c++14 ... -O3 -DNDEBUG -std=c++17 -fPIC ...
```

4. `.gperf` 是**构建期由 gperf 生成**的（连同 `.cpp` 一起落在源码树 `tdutils/generate/auto/`），
   内容含 `register`。clang 在 C++17 下把 `-Wregister` 判为 **error**（C++14 下只是 warning）：

```
$ echo 'int f(){ register int x = 0; return x; }' > r.cpp
$ clang++ -std=c++17 -c r.cpp              → error，exit=1
$ clang++ -std=c++17 -Wno-register -c r.cpp → OK，exit=0
$ clang++ -std=c++14 -c r.cpp              → OK，exit=0
```

## 推荐方案（最小、且不动源码/生成物/profile）

```python
tc = CMakeToolchain(self)
tc.extra_cxxflags.append("-Wno-register")   # 经 CONAN_CXX_FLAGS -> CMAKE_CXX_FLAGS_INIT 注入，不依赖 shell 环境变量（R33）
tc.generate()
```

- 只抑制 `register` 一个「C++17 移除特性」诊断，不降低语言级别、不放宽其他警告；
- 生成物与上游源码零改动（`patches/` 保持为空）；
- 复验：`make -j20` → exit 0，0 error。

## 反模式（禁止）

| 反模式 | 为什么禁止 |
|---|---|
| 给 `patches/` 打 `.gperf`/生成 `.cpp` 的补丁 | 生成物每轮重建，补丁必被覆盖；还会把生成物写进源码树产生脏 diff |
| 把 `CMAKE_CXX_STANDARD` 压回 14 | 包元数据 `cppstd=17` 与实际编译语言级别错位；全局降级会掩盖真正的 C++17 不兼容 |
| 只加 `-Wno-deprecated-register` | C++17 下该开关管不到 `-Wregister`（这是本次踩坑点） |

## 与既有条目的关系（含框架预审判定）

`draft-review` 输出：`signature=✅ root_cause=✅ rec=✅`，
相似正式条目 TOP3 → **E293 score=0.41（sig=0.62）**、E096 0.08、E250 0.05，
📌 预审建议 **review-similar → E293**（灰区，需人工判断）。

- `E293` 讲的是「2003 年前后的 C++ 代码使用 `throw(Type)` 与 `register`（C++17 一律移除）」——
  **同一个被移除特性**，但 E293 的场景是**手写源码**、修法是改源码/降标准；
  本条的增量是：①`register` 出现在**构建期代码生成器（gperf）的输出**里，补丁/改源码都不可行；
  ②根因是 **conan profile 固定 `cppstd=17` 覆盖了工程自加的 `-std=c++14`**（CMake 把标准开关放最后）；
  ③关键在于上游只抑制了 `-Wdeprecated-register`（C++14 拼写），而 C++17 下是 `-Wregister`；
  ④修法是在 toolchain 层加 `-Wno-register`，不动源码/生成物/语言级别。
- `similar_to: E187 / E103`：同属「老工程 + 新工具链默认值」家族，触发点不同。
- **建议处理方式**：由人工在 E293 与独立成条之间二选一。若并入 E293，请把上述 ①~④ 补进其
  `root_cause`/`rec_approach`（E293 现有修法对生成器场景不适用）。
