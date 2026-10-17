# poppler 25.12.0.2 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libpoppler.so 等 3 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied
- 让上游 Find*.cmake 生效：Cairo、GLIB、LCMS2（CMakeDeps 的 config 会抢走 find_package）

## 补丁说明

两个补丁根因相同：`CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`（CMakeToolchain 默认）
让 conan 生成的 `<pkg>-config.cmake` 抢走 `find_package()`，
上游自带的 `Find<Pkg>.cmake` **一次都不跑**。于是 conan 设的是 `<Pkg>_FOUND`（驼峰），
而上游判的是 `<PKG>_FOUND`（全大写），导致上游认为「没找到」——
但 `REQUIRED` 拦不住，因为它**确实找到了**。

### 0001-conan-boost-target-name.patch

上游写 `Boost::boost`，conan 的 boost 包声明的目标名是小写 `boost::boost`。
CMake 目标名大小写敏感，不改会报 `target was not found`。

### 0002-conan-fontconfig-target-name.patch —— 修欠链接

上游 `if(FONTCONFIG_FOUND)` 恒假 → fontconfig **没有被链进去**，
但代码是编进去的。ld.lld 对共享库默认允许未定义符号，**链接期不报错**，
只在运行期炸：

```
Error relocating .../libpoppler.so: FcConfigSubstitute: symbol not found
```

改判 `if(TARGET fontconfig::fontconfig)`，并把上游原分支保留为 `elseif`，
其他平台不受影响。

**注意不能用 `-DFONTCONFIG_FOUND=TRUE` 伪造**：那会让它去链上游写的
`Fontconfig::Fontconfig`，而 conan 声明的是小写目标，直接报
`Target "poppler" links to: Fontconfig::Fontconfig but the target was not found`。
（此路已试过并回退。）

`${FONTCONFIG_VERSION}` 在补丁分支里**不会为空**：它是 poppler 自己在
`CMakeLists.txt:152` 用 `set(FONTCONFIG_VERSION "2.13")` 设的字面量，
是 `find_package` 的入参而非产物，与 MODULE/CONFIG 模式无关。

## 状态
built（真机 conan create + test_package 通过）
