# DRAFT — OHOS CMake 库配方：依赖 find_package 的两道闸

> 状态：草稿，待评审提升为 E 条目。配套 `.kv` 文件同名同目录。
> 来源：`archives/z/zarchive/0.1.2/`（设备实机，2026-09-14）

## 场景

上游 CMake 工程自己去找依赖，而不是把依赖源码 submodule 编进来。于是配方要把
"依赖已由 conan 提供"这件事**完整地翻译成 CMake 能看见的形式**。OHOS 上有两道闸，
任意一道没过，依赖就会以很难读的方式失效。

## 闸 1：find_package 被关在 CMAKE_FIND_ROOT_PATH 里

OHOS 的 `conan_toolchain.cmake` 以交叉模式生成，`find_package` 默认只在
`CMAKE_FIND_ROOT_PATH` 内查找，且 `MODE_PACKAGE=ONLY`。而 CMakeDeps 生成的
`<dep>-config.cmake` 落在 **generators 目录**，默认不在查找根里。

后果分两种，都很隐蔽：

1. 上游用 `find_package(<dep> CONFIG QUIET)` + pkg-config 兜底（zarchive 的
   `cmake/Findzstd.cmake`）→ CONFIG 静默落空，退到 pkg-config 分支，
   而**设备没有 pkg-config**，依赖链直接断掉。
2. 上游 `find_package(<dep> ... QUIET)`，且源码树里恰好有个同名空目录
   （plutosvg 依赖 plutovg 就是这情况）→ 静默编进空目录，直到后面链接期才炸，
   且报错完全指不到 find_package。

### 做法

```python
tc = CMakeToolchain(self)
tc.variables["CMAKE_FIND_ROOT_PATH"] = [self.generators_folder]
tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
tc.generate()
CMakeDeps(self).generate()      # 没有 generator 就没有 config 文件，find_package 必然落空
```

> `CMakeDeps(self).generate()` 必须真的调用：plutosvg 首轮 G2 就死在"只生成
> toolchain、没生成 deps"，`find_package` 静默失败。

## 闸 2：conan 导出的目标名与上游 Find 模块期望的名字对不上

`find_package` 命中不代表依赖目标存在。CMakeDeps 生成的目标名取决于**依赖包
conanfile 的 `cmake_target_name`**：

```python
# archives/z/zstd/1.5.7.1/conanfile.py
self.cpp_info.set_property("cmake_target_name", "zstd::libzstd")
```

而上游 `Findzstd.cmake` 的名字归一化只认这三个：

```cmake
if (NOT TARGET zstd::zstd)
    if (TARGET zstd::libzstd_static)
        add_library(zstd::zstd ALIAS zstd::libzstd_static)
    elseif (TARGET zstd::libzstd_shared)
        add_library(zstd::zstd ALIAS zstd::libzstd_shared)
    endif()
endif()
```

结果 `zstd_FOUND` 为真、`zstd::zstd` 却始终不存在，CMake 配置期报：

```text
Target "zarchive" links to target "zstd::zstd" but the target was not found.
```

### 做法

**在上游 Find 模块既有的名字归一化链条上补一支**，而不是改
`CMakeLists.txt` 的 `target_link_libraries`：

```cmake
        elseif (TARGET zstd::libzstd)
            # Conan's zstd package exports a single target named zstd::libzstd
            add_library(zstd::zstd ALIAS zstd::libzstd)
        endif()
```

理由：把这个 find 模块的职责（把各种查找结果统一到 `zstd::zstd`）补全，是它本来就
该做的事；改业务构建文件则会把包管理器的细节渗进 `CMakeLists.txt`，并且破坏非 conan
构建路径。补丁描述里必须写清"conan 包导出的是哪个名字、依据是它的 conanfile"。

## 别忘了依赖还要能被消费者链接

静态库场景下，包自身链接了依赖，消费者也要能链接到：

```python
self.cpp_info.requires = ["zstd::zstd"]
```

## 验证（zarchive 0.1.2，设备实机）

```text
✅   G0: PASS
✅   G1: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: zarchive 0.1.2
```

- 库级消费者测试 25/25：打包→读回→逐字节比对（256 个字节值全样本、内嵌 NUL 的
  1 KiB 数据、带偏移量读取、目录项计数、缺失路径返回 `ZARCHIVE_INVALID_NODE`）
- CLI 级消费者测试 7/7：对已安装的 `bin/zarchive` 做打包/解包/三文件逐字节 `cmp`/失败码
- 归档全程经 zstd 压缩，**往返成功本身即证明依赖传播正确**

## 边界

- 适用于任何"上游自己 `find_package` 找依赖"的 CMake 工程（CONFIG 模式或自带
  `Find<dep>.cmake`）。
- 若工程用 `pkg_check_modules` 找依赖：闸 1 同样成立（设备无 pkg-config，必须让
  CONFIG 路径命中，或显式提供 `<DEP>_CFLAGS`/`<DEP>_LIBS`）。
- 若工程把依赖源码 submodule 直接编进来：本条目无关。
- 若依赖包的 `cmake_target_name` 恰好与上游期望一致（如 librevenge 设
  `cmake_target_name="librevenge::librevenge"` 而上游就找这个名字）：闸 2 不发生。
