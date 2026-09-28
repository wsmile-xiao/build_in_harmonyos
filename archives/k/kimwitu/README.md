# kimwitu (Kimwitu++)

Kimwitu++ 2.3.13：C++ 编译器构造工具包。从树规格（.k 文件，phylum/operator 定义）
生成 C++ 代码（抽象语法树类、读写、重写与 unparse 规则）。

## 适配说明（2.3.13）

- 源码：官方 GNU Savannah `kimwitu++-2.3.13.tar.gz`（Autotools，自举构建）。
- 产物：`bin/kc++`（kimwitu++ 编译器）+ `share/man/man1/kc++.1`。
- 构建依赖：flex、bison（本机工具链自带，生成 kimwl.cc/kimwy.cc）；
  产物为**静态链接**（libc++_shared 动态版实测无法执行）。

## 关键适配点（实测）

1. **config.status 临时目录**（0001 patch）：autoconf 生成的 config.status 用
   `umask 077 && mktemp -d "./confXXXXXX"` 在当前目录建临时目录并写文件，
   被鸿蒙安全框架拦截（脚本子进程写新建临时目录 → Permission denied）。
   改为 `mktemp -d "$TMPDIR/confXXXXXX"`（无 umask + 绝对路径，
   TMPDIR 指向已存在的可写目录），configure/config.status 才能完成。
2. **kc++ 必须静态链接**（0002 patch）：动态链接的 kc++（依赖
   /system/lib64/libc++_shared.so）执行报 `Operation not permitted`
   （execve EPERM，静态链接同源码可正常执行，实测确认）。
   boot 目标重建 kc++ 时强制 `CXXFLAGSOPT -static`。
3. **boot 的 strip 禁用**（0002 patch）：boot 目标 `strip Gen/kc++`
   原地改写文件被拦（strip: unable to copy file），禁用后 boot 正常完成。
4. **TMPDIR 兜底**：配方 build() 将 TMPDIR 指向已存在可写目录（
   ~/tmp）——安全框架只允许脚本子进程向**已存在的目录**写文件。

## 验证

- 本地完整验证：configure（tmp 修复）→ make（flex/bison + C++ 编译）→
  boot（静态 kc++）→ make install → 安装版 kc++ 运行正常。
- 真实功能：`kc++` 处理最小规格（`Tree: Leaf(child: Tree)`）生成
  test_kimwitu.cc/h（含 `namespace kc` 生成代码）通过。
