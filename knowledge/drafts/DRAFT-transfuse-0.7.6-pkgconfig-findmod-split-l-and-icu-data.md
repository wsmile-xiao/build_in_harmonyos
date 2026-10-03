# DRAFT-transfuse-0.7.6-pkgconfig-findmod-split-l-and-icu-data

## 一句话

`pkg_search_module()` 把 `-l` 放进 `<PREFIX>_LIBRARIES`（FindPkgConfig 用
`--libs-only-l`）、把 `-L` 放进 `<PREFIX>_LIBRARY_DIRS`，上游只链前者 ⇒
裸 `-lxml2`；叠加 FindICU 不查 `data` 组件 ⇒ 静态 ICU 缺 `icudt<ver>_dat`。
两者都在同一个 `CMAKE_PROJECT_INCLUDE` 钩子里补掉。

## 症状（两层，按尝试顺序）

1. `ld.lld-15: error: unable to find library -lxml2` / `-lsqlite3`
2. 补完 `-L` 后：`ld.lld-15: error: undefined symbol: icudt76_dat`
   ```
   >>> referenced by udata.cpp
   >>>   udata.ao:(openCommonData(char const*, int, UErrorCode*)) in archive .../libicuuc.a
   ```

## 根因

**(1) FindPkgConfig 拆变量。** `FindPkgConfig.cmake` 第 636 行：

```cmake
_pkgconfig_invoke_dyn("..." "${_prefix}" LIBRARIES "(^| )-l" --libs-only-l)
```

所以 `LIBXML2_LIBRARIES = -lxml2 -lm`，`-L` 全在 `LIBXML2_LIBRARY_DIRS`。
上游 `src/CMakeLists.txt` 只 `target_link_libraries(transfuse PRIVATE ${LIBXML2_LIBRARIES} ...)`，
从不加 `LIBRARY_DIRS`。实测 `.pc` 本身是对的：

```
Libs: -L"${libdir}" -lxml2 -lm
$ pkg-config --libs-only-L libxml-2.0
-L/root/.conan2/p/.../lib -lxml2 -lm
```

问题纯在 CMake 变量拆分，**不是** E355 的 `.pc` prefix 问题。

**(2) FindICU 只在带组件时查 data。** `FindICU.cmake` 里 `icudata`/`icudt` 只在
`foreach(component ${ICU_FIND_COMPONENTS})` 里被 `find_library(ICU_DATA_LIBRARY_RELEASE ...)`，
而上游写的是 `find_package(ICU REQUIRED)`（无组件）⇒ 配置日志只有
`Found ICU libraries: .../libicuuc.a`，`libicudata.a` 从未被查找。
`icu/76.1` 默认 `shared=False`（`--with-data-packaging=static`），静态归档之间
不存在链接顺序豁免，于是 `libicuuc.a` 对 `icudt76_dat` 的引用悬空。

## 方案（同一个 CMAKE_PROJECT_INCLUDE 钩子）

```cmake
# 路径全部从 Conan 依赖图取，不写死（R49）
link_directories(
    "<icu pkg>/lib"
    "<libxml2 pkg>/lib"
    "<libzip pkg>/lib"
    "<sqlite3 pkg>/lib"
    "<xxhash pkg>/lib"
)
link_libraries("<icu pkg>/lib/libicudata.a")
set(CMAKE_LINK_INTERFACE_MULTIPLICITY 3)
```

`link_libraries()` 的条目排在目标自身库之前，所以 data 归档会先于
`libicuuc.a` 送给链接器；`CMAKE_LINK_INTERFACE_MULTIPLICITY 3` 让静态库重复出现，
使顺序无关。`libicudata.a` 路径用 `icu` 依赖 `cpp_info.libs` 里带 `icudata` 的
那一项 glob 出来，而不是拼字符串。

修正后 link.txt 实测出现 5 个 `-L`，且 `icudata` 解析成功。

## 边界

- 依赖若发布的是共享库且自带 SONAME/`NEEDED`，`-L` 缺失仍会报同样的
  `unable to find library`；本条对「共享 libzip + 静态 libxml2」混合场景同样适用；
- 若上游改用 `PkgConfig::<pkg>::TARGETS` 或 `find_package(... CONFIG)` 消费依赖，
  就不需要 `link_directories`，本条不适用；
- 静态 ICU 是前提。若 `icu/xx` 发布共享版，data 库会作为 `NEEDED` 自动带上。

## 证据

- transfuse 0.7.6，profile `ohos-aarch64-wsl`，clang 15.0.7
- `readelf -d libxml2`/`nm -D --undefined-only` 复核未定义符号来源
- 配方：`archives/t/transfuse/0.7.6/`；修正后 14 个上游 ctest 用例全过
  （含依赖 libzip 的 docx/odt/pptx 6 例）

## 判重说明

- E355 = conan 制品 `.pc` 的 prefix 处理（且该条走的是 meson + boost locale）；
  本条 `.pc` 完全正确，病因在 CMake `FindPkgConfig` 的 `--libs-only-l` ⇒ 不判重；
- E176 = ICU stubdata 动态库在鸿蒙加载器上的限制（动态面）；本条是静态 data 归档
  未被查找到 ⇒ 层与向均不同；
- E534 = musl 缺函数需自建兼容层；本条两个都不是缺函数 ⇒ 不判重。