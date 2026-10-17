# E566 — PkgConfigDeps 引号陷阱与 AC_CHECK_LIB 不进链接线

## 错误特征
```
ld.lld: error: unable to find library -lcurl
```
（-L 路径确实存在、库名正确时）；或：
```
configure: error: cannot run C compiled programs
Error loading shared library libcurl.so: (needed by ./conftest)
```

## 触发条件
- 构建系统: autotools + conan PkgConfigDeps
- 阶段: configure conftest / make 链接
- 典型软件: klavaro 3.14（curl/libintl 都踩）

## 根因分析
两类陷阱叠加：

1. **PkgConfigDeps pc 引号陷阱**：生成的 .pc 里
   `Libs: -L"${libdir}" -lcurl` 带引号变量引用。程序化提取 flags 若
   不展开 `${var}` 并去引号，clang 收到字面 `-L"/path"` 找不到库
   （make -n 看起来正常，实际传参带引号字符）。

2. **AC_CHECK_LIB 不进链接线**：上游 configure.ac 用
   `AC_CHECK_LIB([curl], [curl_global_init])` 只做探测（成功后自动
   追加 -lcurl 到 LIBS，但 klavaro 的 Makefile.am 未使用 $(LIBS) 于
   klavaro_LDADD 之外的链接线实际生效路径）。若在配方里用
   `env.append("LIBS", "-lxxx")` 注入，会污染 configure 的 conftest：
   conftest 链接了这些库但运行时无 LD_LIBRARY_PATH → "cannot run C
   compiled programs"。

3. **make args 引号陷阱**：`autotools.make(args=["LIBS=-L/a -lb"])`
   含空格的变量赋值在 conan 的 shell 化处理中只保留第一个 token，
   后续 -l 丢失（现象：-j2 下 undefined symbol 且手工同命令成功）。

## 解决方案

### 推荐方案（组合拳）
1. 提取 pc flags：循环展开 `${var}` + `t.replace('"','')`
2. `-L` 路径用 LDFLAGS 注入（AC_CHECK_LIB 成功自动加 -l）
3. 缺失的 `-l`（如 proxy-libintl 的 `-lintl`，无对应 AC_CHECK）用
   **补丁直接追加到 src/Makefile.in 的 `xxx_LDADD`**——比 env/make
   args 注入稳定

## 关联
- klavaro 3.14 patches/0003 + conanfile.py `_pc_paths`
- cairo/1.18.4 新 revision 的 fontconfig pin 变更（图对齐背景）
