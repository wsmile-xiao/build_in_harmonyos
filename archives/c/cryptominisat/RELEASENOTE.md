# cryptominisat 版本发布说明

## 5.14.4 (2026-05-20)

### 编译状态
- ✅ 编译成功 (built)
- ✅ 预编译包已生成
- ✅ 3 个补丁已应用

### 平台适配要点
- CMake 需设置 `CMAKE_SYSTEM_NAME=Linux` 以绕过平台识别
- HarmonyOS libcxx 不完整支持 C++20 ranges，需条件编译

### 补丁列表
- 0001-ohos-fix-cpp20-ranges-compatibility.patch
- 0002-ohos-fix-std-ranges-find.patch  
- 0003-ohos-fix-iota-loop.patch

---

## 5.11.22 (2026-05-20)

编译尝试，状态: partial

---

## 5.11.21 (2026-05-20)

编译尝试，状态: partial
补丁: 2 个