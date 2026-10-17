# E6345-draft-zimpl-cmake-install-rpath-tail-colon-eperm：CMake install RUNPATH 尾冒号 EPERM（zimpl 3.7.1）

## 错误特征

```
/data/service/hnp/bin/bash: line 1: <pkg>/bin/zimpl: Operation not permitted
ERROR: zimpl/3.7.1@ohpcd/stable (test package): Error in test() method
	ConanException: Error 126 while executing
```

conan-verify G2 在 test_package 执行包内 bin/zimpl 时，bash 报
`Operation not permitted`（Error 126）。**关键迷惑点**：同一目录下手工
make 构建的 bin/zimpl 可正常执行，conan 缓存 p/bin/zimpl 却 EPERM；把
p/bin/zimpl 复制到任意位置（含 tmp、重写内容）仍然 EPERM，而 build 目录
二进制复制到任意位置均可执行。

## 触发条件

- CMake 项目生成 bin/ 可执行文件，且链接了 conan 仓库动态库（gmp、zlib 等）
- 配方用 `cmake.install()` 安装产物
- 构建期链接命令带 `-Wl,-rpath,/path/to/dep/lib:`（尾冒号=继续搜索默认路径）

## 根因

CMake install() 安装阶段会重写 ELF 的 RUNPATH：把构建期
`/path/to/gmp/lib:`（**带尾冒号**，语义=该目录之后继续搜索默认路径）
规范化为 `/path/to/gmp/lib`（**无尾冒号**，语义=只搜索该目录）。

OHOS musl 动态 loader 对 RUNPATH 语义敏感，无尾冒号的 bin 可执行文件在
execve 阶段被内核拒绝（Operation not permitted / Error 126），即使注入
LD_LIBRARY_PATH 也无效。**1 字节翻转实验铁证**：

- b/build 二进制（RUNPATH 带尾冒号）复制后执行 → 正常
- p/bin 二进制（RUNPATH 无尾冒号）复制后执行 → EPERM
- 把 b/build 二进制第 6311 字节（尾冒号 0x3A）改为 0x00 → **复现 EPERM**
- 把 p/bin 二进制第 6311 字节（0x00）改为冒号 0x3A → **恢复可执行**
- md5 验证翻转后与目标完全一致（唯一差异点即该字节）

## 解决方案

```python
def generate(self):
    ...
    # 保留链接 RUNPATH（配合 package() 覆盖 install 产物）
    tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
    tc.generate()

def package(self):
    cmake = CMake(self)
    cmake.install()
    # 用 build 目录原始 bin 覆盖 install 产物，保留尾冒号 RUNPATH
    from conan.tools.files import copy
    src_bin = os.path.join(self.build_folder, "bin", "zimpl")
    if os.path.isfile(src_bin):
        copy(self, "zimpl", src=os.path.dirname(src_bin),
             dst=os.path.join(self.package_folder, "bin"))
```

验证：`cmp -l p/bin/zimpl b/build/bin/zimpl` 应显示两者一致（或仅 RUNPATH
尾部差异已消除）；`readelf -d p/bin/zimpl | grep RUNPATH` 应保留尾冒号。

## 验证证据

- 修复前：p/bin/zimpl 任意位置执行均 `Operation not permitted`（Error 126）
- 1 字节翻转实验：删除尾冒号→EPERM，补尾冒号→可执行（md5 证实唯一差异）
- 修复后：conan-verify G2/G3/G4/L2/L4/L5 全部 PASS，check.sh 195/198 通过

## 适用与不适用边界

**适用**：CMake 项目 bin/ 可执行文件 + conan 动态库依赖 + OHOS 平台，
症状为 install 产物 execve EPERM 而 build 产物正常。

**不适用**：纯静态链接可执行文件（无 RUNPATH）；共享库 .so 场景（见 E504）；
libheif 式相对路径链接（见 E207）。

## 与既有条目关系

- **相似 E504**（CMake install 期 RPATH_CHANGE 重写 .so 后 loader 无法加载）：
  E504 覆盖 **.so 共享库**场景（症状 Error loading shared library / Error 127）；
  本条目覆盖 **bin 可执行文件**场景（症状 Operation not permitted / Error 126）。
  根因同族（CMake install 期 RPATH 改写）但对象、症状不同，E504 的
  `CMAKE_SKIP_INSTALL_RPATH=TRUE` 方案不解决 bin 尾冒号问题。本条目作
  部分重复补充，新增 **bin 可执行文件 + 尾冒号语义** 诊断价值。
- **相似 E077**（codesign 签名）：同为 install 产物 execve EPERM，但 E077
  根因是签名段失效（需 llvm-objcopy 移除 + binary-sign-tool 重签）；本条目
  根因是 RUNPATH 尾冒号规范化（无签名问题），诊断路径（cmp/readelf 字节级
  对比 vs readelf .codesign 计数）完全不同，不得混用方案。
- **相似 E207/E019**：E207 是 HarmonyOS CMake 相对路径链接项目内库；
  E019 是动态链接器找不到 .so（需 LD_LIBRARY_PATH）。本条目是 loader 拒绝
  execve，均为不同错误签名。

## 新增价值

既有知识库（E504/E077/E019）未覆盖"CMake install 规范化 RUNPATH 尾冒号
导致 bin 可执行文件 execve EPERM、可通过 1 字节翻转实验定位"这一诊断路径
与修复组合；本条目补充 OHOS 上 CMake bin 可执行文件 install 后不可执行的
可复用处理范式（package() 用 build 产物覆盖）。