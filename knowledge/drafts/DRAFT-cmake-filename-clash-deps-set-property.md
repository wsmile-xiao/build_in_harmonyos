# DRAFT — 同名 cmake_file_name 的 Conan 包在 CMakeDeps 同目录互相覆盖

## 问题

同时依赖 `boost1.84/1.84.0` 与 `boost1.84-thread/1.84.0`（两者
`cpp_info.set_property("cmake_file_name", "Boost")`）时，CMakeDeps 在同一
generators 目录生成的 `BoostConfig.cmake`/`BoostTargets.cmake`/
`Boost-Target-release.cmake`/`Boost-*-data.cmake` 整组同名——后安装的包
覆盖先安装的包，主包组件 target（`Boost::filesystem`/`Boost::headers`…）
丢失。

消费者报错形态（二选一）：

```
CMake Error: Could not find a package configuration file provided by "Boost"
```

```
CMake Error: Target "libprojectsrc" links to: Boost::filesystem
but the target was not found.
```

## 根因

Conan 2.x CMakeDeps 的生成文件名由 `cmake_file_name` 决定；拆分包系列
（Debian 风格 boost1.84 / boost1.84-thread / boost1.84-locale…）沿用同一
"Boost" 名。同目录同名文件后写覆盖先写——不是组件缺失，是**整组文件被
换掉了**。

## 修复（推荐）：消费方 generate() 里 deps.set_property 改名

```python
def generate(self):
    deps = CMakeDeps(self)
    # 给其中一个包改独立名（只影响本配方生成目录，不改已发布包）
    deps.set_property("boost1.84-thread", "cmake_file_name",
                      "hocon-boost-thread")
    deps.generate()
```

CMakeLists.txt 对应查找（组件 target 名不变，仍由改名后 config 创建）：

```cmake
find_package(Boost 1.84.0 CONFIG REQUIRED COMPONENTS headers filesystem program_options regex)
find_package(hocon-boost-thread 1.84.0 CONFIG REQUIRED)
# Boost::thread 组件 target 依旧可用
```

## 兜底：链接包级 target

不依赖组件 target，直接链 CMakeDeps 必然生成的包级聚合 target：

```cmake
target_link_libraries(x PRIVATE boost1.84::boost1.84 boost1.84-thread::boost1.84-thread)
```

缺点：丢失组件粒度（链接整包）。

## 配套注意（CMake ≥ 4.0）

`find_package(Boost ...)` 必须带 `CONFIG`——CMake 4.x 移除了 FindBoost
模块（CMP0167），MODULE 模式查找必失败。

## 验证

- cpp-hocon 0.3.0（PR #9258，CI #43232）：改名方案下 conan create 全绿
  （上游 114 TEST_CASE ctest 100% + test_package 消费者断言 6/6）
- 复现命令：`conan install --requires=boost1.84/1.84.0
  --requires=boost1.84-thread/1.84.0 -g CMakeDeps && ls <gen>/ | grep -c
  BoostConfig`（改名前 1 且内容属 thread 包；改主包独占后仍 1 但组件齐全）
