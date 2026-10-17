# DRAFT-9639-minibwa-profile-cc-path-fallback

## profile compiler_executables 路径失效时回退 PATH 解析

### 问题

`conan create` 在 build() 阶段失败：

```
make: /data/service/hnp/bin/clang: No such file or directory
make: *** [Makefile:45: kommon.o] Error 127
```

### 根因

`ci/conan/profiles/ohos-aarch64` 的 `[conf] tools.build:compiler_executables`
硬编码了 CI worker 的工具链布局（`/data/service/hnp/bin/clang`）。在工具链安装在
其他路径的机器上（如本机 PATH 可解析到 `clang` 的另一工具链目录），该绝对路径
不存在；raw Makefile 配方把 conf 值原样传给 `make CC=...`，make 以退出码 127
失败。profile 的 `[buildenv]` 同时把真实工具链 bin/ 前置到了 PATH——这是配方可
利用的回退通道，但 conf 值本身不会自动修正。

### 处理方法

配方读取 conf 后做存在性校验，失败即从 PATH 回退：

```python
compilers = self.conf.get("tools.build:compiler_executables",
                          default={}, check_type=dict) or {}
cc = compilers.get("c", "clang")
if not os.path.isfile(cc):
    cc = shutil.which("clang") or cc
toolchain_bin = os.path.dirname(cc) or None
ar = compilers.get("ar") or (
    os.path.join(toolchain_bin, "llvm-ar") if toolchain_bin else "ar")
# 未显式指定的 binutils 从 cc 的 dirname 推导；同样 isfile 校验 +
# shutil.which(basename) 回退
```

### 落地

minibwa 0.4 配方 `_compiler_tools()`（archives/m/minibwa/0.4/conanfile.py）。
修复后本机与 CI worker 布局均可构建：conf 路径存在时原样使用（保持 CI 语义），
不存在时解析 PATH 中同一工具链。

### 适用范围

所有直接读取 `tools.build:compiler_executables` 并传给 make/自定义构建系统的
Conan 配方（raw Makefile 类）。CMakeToolchain/AutotoolsToolchain 类配方不受
影响（Conan 内部处理编译器解析）。

与 E392 互补（E392 解决 dict 读取方式，本条解决路径不存在回退）；与 E540 互补
（E540 是 runner 环境层的 PATH 前置，本条是配方层的等价容错）。
