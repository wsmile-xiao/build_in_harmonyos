# DRAFT-lldb001 — LibEdit find 模块网络 FS stat 假阴性 → CMakeDeps 目标名遮蔽

**错误签名**：`Target "lldbHost" links to: LibEdit::LibEdit but the target was not found`（CMake configure 期）

## 场景
Conan 上下文（conan create / CI）构建 lldb：`find_package(LibEdit)` 由 LLDBConfig.cmake 的 `add_optional_dependency` 宏（:60）触发。

## 根因链（lldb/0.0.1 G2 首败实测，2026-09-27）
1. 预编译包 `LLVMConfig.cmake:11` 自载 `lib/cmake/llvm` 到 `CMAKE_MODULE_PATH`，`FindLibEdit.cmake` 模块文件存在（llvm/clang 两包均有）。
2. 模块文件在 pkgRedirects 网络 FS 上 **stat 假阴性**（间歇）→ CMake 判定模块不存在 → **回退 config 模式**，命中 CMakeDeps 生成的 `libedit-config.cmake`。判别证据：`CMakeCache.txt` 中 `LibEdit_DIR:PATH=<generators 目录>`（模块命中时不会出现此指向）。
3. CMakeDeps 目标名 = libedit 配方 `package_info` 的 `libedit::libedit`；lldb 源 `Host/CMakeLists.txt` 硬引用 `LibEdit::LibEdit`（`:173-174` 由 `LLDB_ENABLE_LIBEDIT` 门控，`:180` 进 `add_lldb_library`）。
4. CMakeDeps 置 `LibEdit_FOUND=TRUE` → `LLDB_ENABLE_LIBEDIT`（宏 :48 `set(option found)`）为真 → 链接期目标缺失 → 报错。
5. 本地构建（健康 FS）stat 命中 → 模块路径（判别证据 `PC_LIBEDIT_FOUND=1`、`FIND_PACKAGE_MESSAGE_DETAILS_LibEdit=[include][libedit.so][v2.11()]`）→ 本地过、CI 偶发挂。

## 修复（archives/l/lldb/0.0.1/conanfile.py generate()，四层）
1. **显式缓存变量**：`LibEdit_INCLUDE_DIRS`/`LibEdit_LIBRARIES` 预置 → find 模块 find_path/find_library 跳过搜索（FS stat 免疫）。
2. **桥接别名**：CMakeDeps `libedit-config.cmake` 尾部追加 `add_library(LibEdit::LibEdit ALIAS libedit::libedit)`（config 回退兜底）。
3. **模块路径双副本**：`CMAKE_MODULE_PATH` = shim 目录 + monorepo 源树 `llvm/cmake/modules`（FindLibEdit 两份副本，单点 stat 假阴性概率平方级下降）。
4. **tinfo 清除（同链二败，G2_5 实证）**：对同一 `libedit-config.cmake` 后处理（glob+regex）清除 `SYSTEM_LIBS` 中的 `tinfo`——libedit.so 的 `NEEDED libtinfo.so.6` 由动态链接器运行期解析（设备 /usr/lib/libtinfo.so.6 实证存在），消费方链接期不需要 `-ltinfo`；不清除则链接期缺 `libtinfo.a` 硬失败。

## 验证
`grep -E 'LibEdit_DIR|LibEdit_FOUND|PC_LIBEDIT_FOUND' CMakeCache.txt`：模块命中时 `PC_LIBEDIT_FOUND=1` 且无 `LibEdit_DIR=generators`。

## 关联
- 铁律 R35（禁 conan list 判 binary）、R49（依赖注入私有 prefix 同族的确定性注入思想）
- 网络 FS stat 假阴性：E017 同族（ghfast/下载抖动）
