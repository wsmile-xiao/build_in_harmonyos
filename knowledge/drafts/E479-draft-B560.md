# E479: conan test_package 端到端运行 GUI/CLI 二进制时动态库无法加载

## 基本信息
- **严重度**: 2（中）
- **类别**: conan, testing, runtime, ohos
- **来源事件**: wmsmixer 0.5.1 OHOS 适配（test_package 执行 wmsmixer --version 报
  Error loading shared library libX11.so.6/libc++_shared.so）
- **作者**: B560

## 错误特征
```
Error loading shared library libX11.so.6: (needed by .../bin/wmsmixer)
Error loading shared library libXpm.so.4
Error loading shared library libXext.so.6
Error loading shared library libc++_shared.so
Error relocating .../wmsmixer: XCreateGC: symbol not found
```
进程以 exit 32512 失败。

## 触发条件
`package_type = "application"` 的包（GUI/CLI 可执行文件）在 `test_package` 的 `test()`
中**端到端运行被测二进制**（如 `wmsmixer --version`、`--help` 等可在 X 连接前执行的
参数路径）。被测二进制动态链接：
1. conan 依赖库（如 libX11/libXpm/libXext，来自 libx11/libxpm/libxext 包）；
2. `libc++_shared.so` —— OHOS SDK 工具链的 C++ 运行时，**不在 conan 依赖管理范围**。

## 根因分析
- conanrun 环境的 `LD_LIBRARY_PATH` 只覆盖 conan 依赖的 `libdirs`（由 runenv 聚合），
  且**不包含 OHOS SDK 的 libc++ 运行时目录**
  （`/data/service/hnp/ohos-sdk.org/<sdk>/ohos/native/llvm/lib/aarch64-linux-ohos/c++`）。
- `test()` 直接运行被测二进制时，动态加载器找不到依赖库与 libc++_shared.so，
  报 "Error loading shared library ..." 和符号重定位失败（exit 32512）。
- 与链接期 lld 缺 libxml2（E120）、header-library bindirs 不进 PATH（E691 草稿）、
  GNUstep run paths（E449）场景不同——这是 **test_package 运行期**的加载器路径问题。

## 解决方案
在 `test_package/conanfile.py` 的 `test()` 中显式构造运行期 `LD_LIBRARY_PATH`：

```python
ld_paths = []
for dep in self.dependencies.values():
    if dep.package_folder is None:           # 部分依赖对象无 package_folder，跳过
        continue
    for libdir in dep.cpp_info.libdirs or []:
        p = os.path.join(dep.package_folder, libdir)
        if p not in ld_paths:
            ld_paths.append(p)
sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
if os.path.isdir(sdk_libcxx):
    ld_paths.insert(0, sdk_libcxx)
os.environ["LD_LIBRARY_PATH"] = ":".join(ld_paths)
self.run("./test_wmsmixer")                  # 测试程序 popen 执行被测二进制
```

关键注意：
- **Conan 2 `self.run()` 的 `env` 参数必须是 list**（传 dict 报
  `AssertionError: env argument to ConanFile.run() should be a list`），
  直接注入 `os.environ` 再 `self.run()` 最稳妥。
- 遍历依赖时 `dep.package_folder` 可能为 None（build 依赖等），必须跳过。
- SDK libc++ 目录路径不同 SDK 版本会变，建议用 `glob` 或固定当前版本并在
  notes.md 记录。
- 测试程序（test.c）真实执行被测二进制（如 `popen("wmsmixer --version")`）并
  校验输出，满足 R34/PF3 端到端消费者用例要求，而非仅校验 ELF 合规。

## 验证证据
wmsmixer 0.5.1 实测（2026-09-29）：
- 修复前：`conan create` test() 报 32512（动态库加载失败），conan-verify G2 FAIL。
- 修复后（test() 注入依赖 libdirs + SDK libc++）：`wmsmixer --version` 输出
  "wmsmixer version 0.5.1" 且 exit=0，conan-verify G0-G4 全部 PASS。

## 适用边界
- ✅ application 包在 test_package 中端到端运行被测二进制（GUI 的 --version/--help
  无显示前置参数路径、CLI 直接运行）。
- ✅ 被测二进制动态链接 conan 依赖库 + OHOS SDK libc++ 运行时。
- ❌ 纯库包（无 bin 产物）不适用（无运行期动态库问题）。
- ❌ header-library 包（bindirs 不进 PATH）是另一机制（E691 草稿）。

## 不适用边界
- test_package 仅做产物校验（ELF/文件存在）不运行二进制时无需注入。
- 被测二进制静态链接所有依赖（无 NEEDED 库）时无加载问题。

## 关联条目
- similar_to: E120（lld 链接器缺 libxml2.so.16，链接期 LD_LIBRARY_PATH 问题）、
  E691（草稿，header-library bindirs 不进 conanrun PATH）、
  E449（GNUstep run paths 发布）

## 验证命令
```bash
conan create <recipe> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test() 打印 LD_LIBRARY_PATH 应包含依赖 libdirs + /data/service/hnp/ohos-sdk.org/.../llvm/lib/aarch64-linux-ohos/c++
```