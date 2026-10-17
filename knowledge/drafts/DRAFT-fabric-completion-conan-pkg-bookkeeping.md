# DRAFT-fabric-completion-conan-pkg-bookkeeping

## conan 2.x 包根簿记文件：探针全树文件计数必须排除 conaninfo/conanmanifest

### 现象

真机 `conan create` 消费者探针（fabric_completion_probe）第 1 组断言 FAIL：

```
[FAIL] 包全树恰 2 文件
```

其余 27 项断言全 [OK]；本机（Windows MinGW，手工搭建模拟包根）同一探针 5/5 全过。真机包根实际 4 个文件：2 个上游内容文件 + conan 2 写入的 2 个簿记文件。

### 根因

- conan 2 create 在 `package_folder` 根目录写入 **conaninfo.txt** 与 **conanmanifest.txt** 簿记文件
- 探针 `count_recursive(root)` 全树递归计数未排除簿记 → 2 + 2 = 4 ≠ 2
- 本机模拟包根是手工搭建的（只有配方 package() 会安装的 2 个文件），没有簿记文件 → **本机过、真机挂**的环境差
- 配方 `build()` 的防漂移计数检查的是 source_folder（不含簿记），未踩坑；只有指向包根的探针计数会踩

### 推荐方案

探针计数函数排除簿记文件名（与配方 build() 防漂移口径一致）：

```cpp
bool is_bookkeeping(const std::string& name) {
    return name == "conaninfo.txt" || name == "conanmanifest.txt";
}
// count_recursive: else if (S_ISREG(info.st_mode) && !is_bookkeeping(name)) ++n;
```

completions/、doc/ 等子目录本身不含簿记文件，子目录断言无需改变。

参考实现：`archives/f/fabric-completion/1.0/test_package/fabric_completion_probe.cpp`。

### 验证

```
修复前: 真机 conan create → [FAIL] 包全树恰 2 文件（4!=2），probe FAILED
修复后: 本机带簿记模拟包根复测 5/5 全过 → 真机重验 fabric_completion_probe: all assertions passed
```

### 关联

- 与 build() 防漂移清单同口径：配方侧检查 source_folder、探针侧检查 package_folder，两侧都要排除 conan 元数据。
