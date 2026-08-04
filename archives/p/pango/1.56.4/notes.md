# pango 1.56.4 编译笔记（HarmonyOS PC · 标准 Conan meson）

## 定位
- 产出 libpango-1.0.so 等 3 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 补转发型 .pc：cairo-ft=cairo,freetype2、cairo-fc=cairo,fontconfig（conan 只生成 recipe 声明的那一个）

## 补丁说明

### 0001-include-fcfreetype.patch —— 补上缺失的 `<fontconfig/fcfreetype.h>`

pango 1.56.4 在 `pango/pangofc-fontmap.c` 的 `pango_fc_font_map_add_font_file()`
（约 4010 行）直接调用 `FcFreeTypeQueryAll`，但**全树没有任何地方 include
`<fontconfig/fcfreetype.h>`** —— 该函数只声明在那个头里，`fontconfig.h` 不含。
已在 fontconfig 2.18.1 包与 mac homebrew 两处核实，grep 计数均为 0。

多数平台上隐式函数声明只是警告，所以上游一直没暴露；clang 带 `-Werror` 时是硬错误：

```
error: call to undeclared function 'FcFreeTypeQueryAll'
  [-Werror,-Wimplicit-function-declaration]
```

补上正确的头即可 —— 符号本身在 `libfontconfig.so` 里确实导出，不是缺实现。
补丁为一行 include，不含任何注释注入。

## 状态
built（真机 conan create + test_package 通过）
