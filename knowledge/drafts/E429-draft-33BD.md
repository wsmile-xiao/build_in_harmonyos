# E429 — CMake pkg_check_modules 只链接 ${PROJECT_DEPS_LIBRARIES} 未用 _LIBRARY_DIRS 导致传递 -L 丢失

## 错误特征

```
ld.lld: error: unable to find library -lcairo-gobject
ld.lld: error: unable to find library -ljpeg
ld.lld: error: unable to find library -lturbojpeg
ld.lld: error: unable to find library -lzstd
...
clang-15: error: linker command failed with exit code 1
```

链接 `libayatana-ido3-0.4.so`（CMake + pkg_check_modules + Conan PkgConfigDeps）时，传递依赖库全部找不到。

## 触发条件

- 构建系统: cmake
- 阶段: linking
- 前置: 上游 CMakeLists.txt 使用 `pkg_check_modules(PROJECT_DEPS REQUIRED glib-2.0 gtk+-3.0)` 且
  `target_link_libraries(target ${PROJECT_DEPS_LIBRARIES})`
- 依赖注入: Conan PkgConfigDeps 生成的 .pc 链路（gtk/glib 生态，传递依赖 cairo-gobject、
  libjpeg-turbo、zstd、tiff、webp、pixman 等）

## 根因分析

`pkg_check_modules` 会把 pkg-config 解析出的 **-L 搜索路径**存入
`PROJECT_DEPS_LIBRARY_DIRS`，把库名存入 `PROJECT_DEPS_LIBRARIES`。上游只链接了
`${PROJECT_DEPS_LIBRARIES}`，未把 `PROJECT_DEPS_LIBRARY_DIRS` 传入
`target_link_directories()`，导致所有传递依赖库的 -L 路径丢失，链接器无法解析
`-lcairo-gobject`/`-ljpeg`/`-lzstd` 等。这是一个跨库可复现的上游 CMake 编写模式问题。

## 解决方案

### 推荐方案

在 conanfile.py 的 `generate()` 中遍历依赖图，把全部依赖包的 `lib` 目录显式注入
链接标志（不依赖上游是否传播 LIBRARY_DIRS）：

```python
def generate(self):
    PkgConfigDeps(self).generate()
    tc = CMakeToolchain(self)
    link_dirs = set()
    for dep_name, dep in self.dependencies.items():
        if dep.package_folder:
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                link_dirs.add(f"-L{libdir}")
    flags = " ".join(sorted(link_dirs))
    tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = flags
    tc.variables["CMAKE_EXE_LINKER_FLAGS"] = flags
    tc.generate()
```

要点：
- 遍历 `self.dependencies.items()` 而非硬编码名单（cairo-gobject 等独立包名易遗漏）
- 对 `package_folder` 判空后再 `os.path.join`
- `-L` 同时注入 shared/exe 链接标志，覆盖共享库与可执行目标

### 禁止做法

- ❌ 把 `CMAKE_SHARED_LINKER_FLAGS` 覆盖为替换式而非追加式（会丢已有 flags）
- ❌ 只修上游 CMakeLists 改 target_link_directories（污染上游源码，违反 R1 参数最少化）
- ❌ hardcode 某台机器的 cache 路径（违反 R39 / 原子性审计）

## 验证

```bash
conan create archives/a/ayatana-ido/0.10.4 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing   # exit 0
# 链接产物完整：libayatana-ido3-0.4.so 含 cairo-gobject/jpeg/zstd/tiff/webp 传递依赖
# test_package ctest 1/1 PASS, test_ayatana-ido: PASS
```

## 四范围查重

- knowledge/graph/: 未命中精确条目。E278（restore-cmake-target-definition）是条件目标
  定义问题；E468（append-generators-folder-to-pkg-config-path）是 autotools
  PKG_CONFIG_PATH 问题；E480（same-track-transitive-headers）是 header-only 传递，
  与本条 CMake -L 传播机制均不同。
- knowledge/doc/、knowledge/drafts/、index.tsv: 均无同类条目。
- 结论: 路径 B 成立（新增、可跨库复用）。

## 关联条目

- 相似: E278（target_link_libraries 相关）, E468（PkgConfigDeps 路径）
- 来源: ayatana-ido 0.10.4 适配 (r01)