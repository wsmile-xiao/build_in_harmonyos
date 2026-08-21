# E257 — CMake install 期 RPATH_CHANGE 重写 .so 后 musl loader 无法加载

## 错误现象

- conan create 构建成功，但 test_package 运行 `./test_bin` 报：
  `Error loading shared library libX.so: (needed by ./test_bin)` exit 127
- 即使 LD_LIBRARY_PATH 正确指向包含 libX.so 的目录仍失败
- 同目录下未链接依赖库的 .so（如 libubox.so，仅依赖 libc.so）可正常加载，
  而链接了依赖库（json-c 等）的 .so 全部失败

## 根因

- CMake install 阶段对带 RUNPATH 的目标执行 `file(RPATH_CHANGE OLD_RPATH=... NEW_RPATH="")`，
  重写 .so 的 dynamic 段
- 改写后的产物在 OHOS musl loader 下无法加载（字节与构建产物不一致，
  `cmp` 可验证 md5/内容差异），平台限制
- 判定依据：构建目录 `b/build/Release/*.so` 可加载、安装目录 `p/lib/*.so` 不可加载，
  二者 md5 不同

## 修复方案

1. conanfile.py `generate()` 设置 `tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = "TRUE"`
2. `package()` 中 `CMake(self).install()` 之后，用构建产物覆盖被改写的文件：

```python
build_dir = os.path.join(self.build_folder, str(self.settings.build_type))
for name in ("libX.so", "libY.so", "tool"):
    hits = glob.glob(os.path.join(build_dir, "**", name), recursive=True)
    if hits:
        shutil.copy2(hits[0], os.path.join(self.package_folder, sub, name))
```

## 先例

- libubox 2026-06-19（json-c 依赖，libblobmsg_json.so/libjson_script.so 受影响）

## 验证

```bash
cmp p/lib/libblobmsg_json.so b/build/Release/libblobmsg_json.so  # 应一致
LD_LIBRARY_PATH=p/lib ./test_bin   # 应 exit 0
```
