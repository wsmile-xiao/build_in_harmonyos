# DRAFT-expat-2.8.4-cmake-getrandom-default-auto-6371：bump 时熵源选项默认值被上游改成 AUTO

## 现象

把 expat 配方从 `2.8.2` 线（2.8.2.1.1）bump 到上游 `R_2_8_4` 时，核对新源码发现：
2.8.2 时代 cmake 的 `EXPAT_WITH_GETRANDOM` 默认 **OFF**（旧配方注释：expat 默认
`EXPAT_WITH_*=OFF` 不启用任何熵源 → 运行期缺熵，须显式 `=ON`）；
而 2.8.4 的 `CMakeLists.txt` 变成：

```text
expat_shy_set(EXPAT_WITH_GETRANDOM "AUTO" CACHE STRING "Make use of getrandom function (ON|OFF|AUTO) [default=AUTO]")
...
evaluate_detection_results(EXPAT_WITH_GETRANDOM HAVE_GETRANDOM "function getrandom" ...)
```

——默认值从 OFF 翻成 **AUTO**，并新增自动探测分支。

## 根因与风险

这不是新增开关，而是**既有显式选项的语义随上游版本漂移**。纯版本 bump 若只改
url/sha256/version、沿用「这选项我旧版本已经显式开过」的直觉而不重新核对新
CMakeLists 的默认与探测口径，会有两种失效方向：

- 新版本默认恰好覆盖需求 → 旧显式值变冗余，但无害（本次即属此类，显式 `=ON`
  与 AUTO 探测出的结果一致或更强）；
- AUTO 的配置期探测（`check_symbol_exists` 等编译/链接探测）在 OHOS 交叉 sysroot
  上的判定与真机 libc 实际能力存在差异 → 悄悄退化为无熵源而不报错。

## 可复用修复模式

跨小版本 bump 一个"成熟 cmake 配方"时，把配方 build() 里**显式传过的每个 cache 选项**
逐个到新版本 `CMakeLists.txt` 里 diff 其 `set(... CACHE ...)` 默认值与取值集合；
凡默认值/探测语义变化的选项，继续显式传确定性取值，让新版本行为与**已验证的旧线一致**，
而不是信任新的 AUTO。expat 2.8.4 因此继续传 `-DEXPAT_WITH_GETRANDOM=ON`，
并保留 `EXPAT_BUILD_TESTS=ON` + 构建后直接跑 `tests/runtests` 作为回归证据。

## 验证证据

bump PR 以 runtests 实跑输出为通过率依据（2.8.2 线实测 `Checks: 4824, Failed: 0`；
2.8.4 以本 PR CI 输出为准），不从源码声明估算；熵源配置不退回宏式
`XML_DEV_URANDOM` 等与上游构建系统不一致的路径。
