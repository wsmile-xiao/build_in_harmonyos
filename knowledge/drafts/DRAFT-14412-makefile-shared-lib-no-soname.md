# DRAFT-14412: 手写 Makefile 共享库链接规则缺 -Wl,-soname → 产物无 DT_SONAME（CI L5a）

- **来源**：tomlc99 0.0-git20260130 适配（2026-10-03，j669539）
- **领域**：构建系统/链接/打包（手写 Makefile 项目）
- **邻近但不同**：E383（CMake 侧——OHOS 无 Platform/HarmonyOS.cmake 致 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 不注入）、E330（expat 版本化 SONAME 被剥）、E274/E316（运行期按 SONAME 寻址失败）——均为 SONAME 主题但根因在 CMake/运行期，本条是 Makefile 链接规则层，图谱未命中

## 现象

手写 Makefile 的 C/C++ 库项目（无 configure、无 CMakeLists），共享库规则形如：

```makefile
libtoml.so.$(LIB_VERSION): toml.o
	$(CC) -shared -o $@ $^
```

`conan create` 全流程成功，但 CI L5 门禁报：

```
[fail] L5a: libtoml.so.1.0 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
       [hint] 在 CMakeLists.txt 中设置 set_target_properties(... PROPERTIES SOVERSION x.y)
```

本地复现：`readelf -d libtoml.so.1.0 | grep SONAME` 无任何输出。

## 根因

链接命令行从未携带 `-Wl,-soname`：

- CMake 工程靠平台模块（Platform/Linux.cmake）的 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"` 在生成链接命令时自动注入 SONAME（OHOS 侧无此模块即 E383）；
- autotools 靠 libtool 的 `-soname` 传递；
- **手写 Makefile 既无平台模块也无 libtool**，作者忘记写就永远没有——该缺陷与目标平台无关（glibc Linux 上同样缺失），只是 CI L5a 把它显式拦下。

## 修复

补丁给共享库规则注入**相对** SONAME，版本号复用 Makefile 自己的 `LIB_VERSION`（避免双源漂移）：

```diff
 libtoml.so.$(LIB_VERSION): toml.o
-	$(CC) -shared -o $@ $^
+	$(CC) -shared -Wl,-soname,libtoml.so.$(LIB_VERSION) -o $@ $^
```

配方 `package()` 侧配套生成开发符号链接（`-ltoml` 链接解析用；R5: 先 rm -f 再 ln -s）。

## 验证

- `readelf -d lib/libtoml.so.1.0` 输出 `(SONAME) Library soname: [libtoml.so.1.0]`（相对路径）
- tomlc99 0.0-git20260130 本地 conan create（ohos-aarch64 profile）L5 pass
- 反向验证：不打补丁时 readelf 无 SONAME 条目（本机实测）

## 红线

- SONAME 必须是**相对文件名**（`libtoml.so.1.0`），绝对路径触发 L5a 另一条款
- 不要用 CMake 的 hint（`set_target_properties SOVERSION`）修 Makefile 项目——那是另一个构建系统的语言
- 若上游 Makefile 已把 `$(LDFLAGS)` 接进共享库规则，优先 `make LDFLAGS="-Wl,-soname,..."` 免补丁注入；tomlc99 未接，只能 patch
