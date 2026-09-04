# jbjg 2.1 编译笔记（HarmonyOS PC · 手写 Makefile 静态库）

## 定位
- JBIG-KIT（ITU-T T.82 无损图像压缩）；本任务发布 `libjbig.a` 静态库。
- 产出 **静态库 libjbig.a** + 头 `jbig.h`/`jbig_ar.h`。`package_info.libs = ['jbig']`，无外部依赖。

## 为什么手写（生成器不支持）
jbigkit 用**手写 Makefile**（非 cmake/autotools/meson），`conan_packager gen` 只支持那三种，故本配方**全手写**。

## 关键适配（build()）
- **CMakeLists 无**：`libjbig/` 下使用 `make all check`；`check` 只运行测试目标，必须显式先构建 `all` 才会生成待打包的 `libjbig.a`/`libjbig85.a`，随后执行上游官方测试。
- **工具变量**：build() 只在 Conan 源码副本中把字面 `ar rc`/`ranlib` 替换为解析到的 llvm-ar/llvm-ranlib，并追加 `check: test` 别名；缺失工具即 fail-closed。
- **CC/CFLAGS**：走 `tools.build:compiler_executables`，命令行固定 `-O2 -W -Wno-unused-result`，静态库启用 `-fPIC`。
- **静态库无 .so**：无需代码签名；test_package 使用 `find_package(JBIG)` 链接并调用 `jbg_dec_init/free`。

## 验证结果
- 官方源码归档 SHA-256：`DE7106B6BFAF495D6865C7DD7AC6CA1381BD12E0D81405EA81E7F2167263D932`。
- 真机 W3 r4：`conan create` RC 0；T.82/T.85 上游测试和 `test_package` 的 `jbg_dec_init/free` 均通过。
- r3 失败复盘：仅运行 `check` 会导致 package 缺少 `libjbig.a`，CMakeDeps 报 `Library 'jbig' not found in package`；改为 `all check` 后闭环。

## 状态
**状态**：W3 真机验证通过（r4）。
