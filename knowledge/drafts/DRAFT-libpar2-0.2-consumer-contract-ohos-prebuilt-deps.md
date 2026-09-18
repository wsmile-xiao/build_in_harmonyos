# 预编译依赖 CMakeDeps 契约与消费者适配

> 草稿（DRAFT）。与同目录 `DRAFT-libpar2-0.2-consumer-contract-ohos-prebuilt-deps.kv` 成对。
> 来源：libpar2 0.2 适配（本 PR），任务 libpar2-0.2-r01-pc1-39-20260916T130221Z。

## 现象（四类独立问题，均发生在消费者/test_package 侧）

1. **预编译依赖头文件找不到**：
```text
fatal error: 'sigc++/sigc++.h' file not found
```
libpar2 公开头 `par2repairer.h` include `<sigc++/sigc++.h>`，而 ohpcd 预编译
libsigc/2.12.1 二进制的 CMakeDeps 数据 `libsigc_INCLUDE_DIRS_RELEASE` 为空
（配方 package_info 明明声明了 includedirs）。

2. **库名带 lib 前缀导致找不到**：
```text
CMake Error: Library 'libpar2' not found in package.
  If 'libpar2' is a system library, declare it with 'cpp_info.system_libs'
```
`lib_LTLIBRARIES = libpar2.la` 产物是 `libpar2.a`，CMakeDeps 的 find_library
自动补 "lib" 前缀，`cpp_info.libs=["libpar2"]` 会错误查找 `liblibpar2.a`。

3. **两阶段 API 直接调用 Process 崩溃**：
```text
Par2Creator::Process -> 0
PASS: PAR2 file created: consumer-data.par2
Verifying source files:
Signal 11 (core dumped)
```
上游 0.2 的 `Par2Repairer::Process` 中加载步骤（LoadPacketsFromFile 等）位于
`PreProcess()`，直接调 `Process()` 时 `mainpacket` 为空 → SegFault。

4. **上游 glob 安装头文件失效**：
```text
fatal error: 'libpar2/par2cmdline.h' file not found
```
`library_include_HEADERS = *.h`（Makefile.am glob）在 OHOS 构建环境未展开，
包内 `include/libpar2/` 只有 `config.h`。

## 根因与修复

### (1) 预编译依赖 CMakeDeps INCLUDE_DIRS 为空
预编译二进制来自制品仓，其 CMakeDeps 数据缺 include 目录（E216 同族但触发点
是二进制数据而非 components 传播）。修复：test_package 生成器用依赖标准接口注入。

```python
# test_package/conanfile.py generate()
tc = CMakeToolchain(self)
if "libsigc" in self.dependencies:
    dep = self.dependencies["libsigc"]
    pf = getattr(dep, "package_folder", None) or ""
    incs = [i if os.path.isabs(i) else os.path.join(pf, i)
            for i in dep.cpp_info.includedirs]
    tc.variables["LIBSIGC_INCLUDE_DIRS"] = ";".join(incs)
tc.generate()
```
```cmake
# CMakeLists.txt
if(DEFINED LIBSIGC_INCLUDE_DIRS)
    target_include_directories(test_libpar2 PRIVATE ${LIBSIGC_INCLUDE_DIRS})
endif()
```
同时配方 `package_info()` 用 `cpp_info.requires = ["libsigc::libsigc"]`
把接口依赖（头文件传递）传给下游。

### (2) cpp_info.libs 填短名
autotools `lib_LTLIBRARIES = libpar2.la` → 产物 `libpar2.a` → 库名是 `par2`：
```python
self.cpp_info.libs = ["par2"]   # 不是 ["libpar2"]
```

### (3) 两阶段 API 先 PreProcess 再 Process
```cpp
Par2Repairer repairer;
repairer.PreProcess(cmd);        // 加载 packets/创建源文件列表
Result r = repairer.Process(cmd, false);  // 校验
```

### (4) package() 显式安装头文件
```python
from conan.tools.files import copy
copy(self, "*.h", self.source_folder,
     os.path.join(self.package_folder, "include", "libpar2"),
     keep_path=False)
```

## 验证

```bash
conan create archives/l/libpar2/0.2 --user=ohpcd --channel=stable   # test_package 编译+运行
# 消费者输出：Par2Creator::Process -> 0 / PreProcess -> 0 / Process(verify) -> 0
```
libpar2 0.2 实测：四项修复后 conan-verify G1-G4、L2/L4/L5 全 pass；
w3-local-ci JC/L0 全 pass。修复顺序即现象 1→2→3→4 的排查顺序。

## 适用边界 / 反例

- 适用于消费预编译二进制依赖（CMakeDeps INCLUDE_DIRS 空）的 C++ 库；
  autotools 库名带 lib 前缀；两阶段 API 旧式库；Makefile.am HEADERS glob 库。
- 反例：从源码本地构建依赖（CMakeDeps 数据含 include）时问题 (1) 不出现；
  新式 API 单阶段 Process 时问题 (3) 不出现。
- (3) 的 SegFault 根因是 API 调用约定而非平台缺陷——不能当成 HMDFS/平台限制。

## 查重差异

- 与 E216（CMakeDeps components include 不传播）：根因相似但触发点是**预编译
  二进制数据文件**，修复在 test_package generate() 用 dependencies cpp_info 注入
  （E216 是 glob-fallback 上游侧）。
- 与 E221（library 契约建模）：补充 find_library "lib" 前缀与 autotools 库名的
  具体对应关系（libpar2.la → "par2"）。
- 与 E217/E309（头文件安装）：补充 automake `HEADERS = *.h` glob 未展开边界。
