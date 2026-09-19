# E6344-draft-zimpl-bison-pkgdatadir-redirect：bison pkgdatadir 重定向（zimpl 3.7.1）

## 错误特征

```
bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory
make[2]: *** [src/CMakeFiles/libzimpl.dir/build.make:75: src/zimpl/mmlparse2.c] Error 1
```

发生在 conan create 的 CMake build 阶段：`bison_target(MMLPARSE2 ...)` 调用的 bison
能正常启动，但无法打开其内嵌数据目录 `/share/bison/m4sugar/m4sugar.m4`。

## 触发条件

- 使用 conan 制品仓的 `bison/3.8.2` 作为 `tool_requires`
- 项目 CMake 使用 `bison_target`/`flex_target` 从 `.y`/`.l` 源生成解析器
- bison 包在编译时被配置 `--prefix=`（空前缀），导致 `pkgdatadir` 编译期内嵌为
  `/share/bison` 绝对路径，与实际安装位置（conan 包内 `share/bison/`）不一致

## 根因

conan 的 `bison/3.8.2` 包构建配置使 bison 二进制内嵌了不存在的绝对数据路径
`/share/bison`。bison 在生成解析器时查找 `m4sugar.m4`（位于 pkgdatadir 的
`m4sugar/` 子目录），找不到即退出。BISON_PKGDATADIR 环境变量可覆盖内嵌路径。

bison 生成解析器还需要 m4 宏展开器，因此不仅要重定向 `BISON_PKGDATADIR`，还要
提供 `m4` 工具依赖并设置 `M4` 环境变量指向其 bin/m4。

## 解决方案

```python
def build_requirements(self):
    self.tool_requires("bison/3.8.2")
    self.tool_requires("flex/2.6.4.2")
    self.tool_requires("m4/1.4.19")   # bison 运行时需要 m4 宏库

def build(self):
    bison_pkg = self.dependencies.build["bison/3.8.2"].package_folder
    m4_pkg = self.dependencies.build["m4/1.4.19"].package_folder
    os.environ["BISON_PKGDATADIR"] = os.path.join(bison_pkg, "share", "bison")
    os.environ["M4"] = os.path.join(m4_pkg, "bin", "m4")
    cmake = CMake(self)
    cmake.configure()
    cmake.build()
```

必须在 build()（configure 之前的任何位置，实际在 cmake.configure() 前）设置上述
环境变量；设置后 bison 生成的 `mmlparse2.c`/`mmlscan.c` 位于 CMake binary dir。

## 验证证据

- 修复前：conan-verify G2 失败，日志含 `bison: /share/bison/m4sugar/m4sugar.m4: cannot open`
- 修复后：G2 通过，`[BISON][MMLPARSE2] Building parser with bison 3.8.2` 成功，
  `mmlparse2.c` 正常生成，后续编译链接、check.sh 195/198 通过

## 适用边界

**适用**：任何 CMake + bison_target/flex_target 的 conan 配方；bison 包 pkgdatadir
内嵌为绝对路径的 OHOS/通用 Linux 场景。

**不适用**：系统自带 bison（`/data/service/hnp/bin/bison`）且数据目录完整的场景；
不通过 bison 生成解析器的项目无需此处理。

## 与既有条目关系

- **similar_to E540**（runner-path-prepend）：E540 是 OHOS runner PATH 缺少
  `/data/service/hnp/bin` 导致 make 不可见；本条目是 bison 内嵌 pkgdatadir 失效。
  两者同属"conan 构建工具在 OHOS 上路径/环境注入"类别，但根因、错误签名与注入
  变量完全不同。
- **类似先例**：ball 1.5.0 配方（archives/b/ball/*/conanfile.py）已采用同款
  BISON_PKGDATADIR + M4 + m4/1.4.19 处理，本例证实了该模式的普适性并给出
  bison_target 场景的错误签名证据。

## 新增价值

既有知识库（E540 等）未覆盖"bison 内嵌 pkgdatadir 失效 → BISON_PKGDATADIR/M4
重定向"这一具体错误签名与修复组合；本条目补充了 OHOS 上 bison 解析器生成类
CMake 项目的可复用处理范式。