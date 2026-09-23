# DRAFT — header-only test_package 消费者源码后缀与项目语言不匹配

## 问题概述

conan-init 为 C 类项目生成的 test_package 模板默认创建 `test.c` 并声明 `project(... C)`。当目标库是 C++（header-only 库尤其常见）时，消费者测试必须用 C++ 代码真实调用被测包 API（R34），此时把 `project()` 改为 CXX 后，残留的 `.c` 后缀源文件会让 CMake 在 CXX-only 工程中找不到 C 语言链接器，configure 阶段直接报：

```
CMake Error: Cannot determine link language for target "test_picojson".
CMake Error: CMake can not determine linker language for target: test_picojson
```

## 典型错误

```
CMake Error: Cannot determine link language for target "test_picojson".
CMake Error: CMake can not determine linker language for target: test_picojson
ERROR: picojson/1.3.0@ohpcd/stable (test package): Error in build() method, line 27
	cmake.configure()
```

触发条件：
- 构建系统: CMake（test_package 由 conan-init 模板生成后手工改写）
- 阶段: configure（CMake generate）

## 根因

1. CMake 按源文件后缀决定语言：`.c` 视为 C 源，`.cc/.cpp` 视为 C++ 源。
2. `project(test_picojson CXX)` 只启用 C++ 语言，不注册 C 编译器。
3. CXX-only 工程里出现 `.c` 源 → CMake 无法为该目标确定链接语言（没有 C 链接器规则）→ generate 阶段硬失败。
4. conan-init 默认模板是 `project(test_picojson C)` + `test.c`；从 C 模板改 CXX 时容易漏改源文件后缀。

## 解决方案（已验证）

C++ 消费者测试源统一使用 `.cc` 后缀，并同步更新三处引用：

```bash
git mv test_package/test.c test_package/test.cc
# test_package/CMakeLists.txt: add_executable(test_picojson test.cc)
# test_package/MANIFEST.yml:   file: test.cc
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <name> <ver>
```

验证结果：conan-verify G1/G2 全 PASS，test_package 二进制编译链接成功并通过 CTest。

回退方案（保留 .c 后缀）：`project(test_picojson C CXX)` 同时启用两种语言，或对单个源文件
`set_source_files_properties(test.c PROPERTIES LANGUAGE CXX)`。

## 适用边界

- 适用：header-only / 纯头 C++ 库的 test_package 消费者测试；任何 CXX-only CMake 工程。
- 反例：纯 C 库（project(... C) + test.c）不受影响；已有 CMake 源后缀规范的项目不受影响。
- 关联：与 E307（test_package 无 CMake 直编）同属 header-only test_package 陷阱面，但错误签名与修复动作不同。

## 验证与查重

- 验证库：picojson 1.3.0（本 PR），conan-verify G2 PASS。
- 查重：知识图谱索引无 "link language" 条目；engine 对 "Cannot determine link language" 命中 E053（cc1plus，属误命中不相关）；drafts/ 无同主题条目 → 未命中，新增草稿。
