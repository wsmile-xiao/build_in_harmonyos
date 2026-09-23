# DRAFT — Conan package() 中 copy() 的 dst 必须用 package_folder 绝对路径

## 问题概述

手写 Conan 2 配方（尤其 header-only 库，没有 cmake install 流程）时，`package()` 里常用
`copy()` 把头文件装入包目录。若 dst 写成相对路径（如 `dst="include"`），Conan 的
`copy()` 按 Python 进程当前工作目录解析该路径，而 `package()` 执行时 CWD 是构建目录、
不是包目录，结果文件落到别处，包目录为空：

```
picojson/1.3.0@ohpcd/stable: Calling package()
picojson/1.3.0@ohpcd/stable: package(): WARN: No files in this package!
```

消费者（test_package）随后在 CMake configure 阶段失败：

```
CMake Error in CMakeLists.txt:
  Imported target "picojson::picojson" includes non-existent path
  ".../.conan2/p/b/picoj.../p/include"
```

## 典型错误

```
package(): WARN: No files in this package!
Imported target "picojson::picojson" includes non-existent path ".../p/include"
ERROR: picojson/1.3.0@ohpcd/stable (test package): Error in build() method, line 27
	cmake.configure()
```

触发条件：
- 构建系统: 无（header-only / 纯手写 package()）
- 阶段: packaging（package() 拷贝）、test_package configure

## 根因

1. `conan.tools.files.copy()` 的 dst 相对路径按进程 CWD 解析（`os.path.join` 到当前目录）。
2. Conan 在 package() 阶段把 CWD 设在构建/导出相关目录，不是 package_folder。
3. `dst="include"` 实际写到了 CWD/include；包目录没有文件 → 空包。
4. CMakeDeps 生成的 target 根据 recipe 的 cpp_info 指向 `<pkg>/include`，空目录 → "non-existent path"。

## 解决方案（已验证）

dst 使用 `os.path.join(self.package_folder, ...)` 绝对路径：

```python
def package(self):
    copy(self, "picojson.h", src=self.source_folder,
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "LICENSE", src=self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
```

验证结果：`package(): Packaged 1 '.h' file: picojson.h`，test_package 配置/编译/CTest 全通过。

回退方案：若上游有 CMake install/export，用 `cmake.install()`（E321/E322 的 header-only cmake
路线）由 CMake 保证安装目标正确。

## 适用边界

- 适用：header-only / 数据 / 无构建族配方的 package()；任何手写 copy() 到包目录的配方。
- 反例：使用 CMake/autotools install 的配方（install 流程内部已指向 package_folder）；仅拷贝 meta 文件且不依赖 CWD 的场合。
- 关联：与 E321/E322（header-only cmake install 路线）、E392（raw-makefile 配方三陷阱）同属 Conan 2 header-only 打包陷阱面，但错误签名、阶段与修复动作均不同。

## 验证与查重

- 验证库：picojson 1.3.0（本 PR），conan-verify G2 PASS。
- 查重：知识图谱索引无 "No files in this package" 条目；engine 命中 E292（Arrow 类测试环境，属误命中不相关）；drafts/ 无同主题条目 → 未命中，新增草稿。