# halibut 1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. CMake Configure
cmake -S . -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5

# 2. Build
cmake --build build -j2

# 3. Install
cmake --install build --prefix $DEFAULT_PREFIX --strip
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4 策略兼容性错误 | CMake 4 移除了对 CMake < 3.5 策略的兼容支持 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | `/tmp` 只读 | HarmonyOS 的 `/tmp` 为只读文件系统 (E002) | 使用 `$TMPDIR` 环境变量路径 |
| 3 | 安全弹窗 (R7) | 首次执行新二进制时 HarmonyOS 弹出确认框 | 需要 UI 交互触发确认 |
| 4 | settings.yml 缺少 OHOS 枚举 | 标准 Conan 无 OHOS 平台支持 | 添加 `OHOS: version: ["6.0"]` 到 settings.yml |

## 依赖版本

无外部运行时依赖（仅使用 C 标准库）

## 验证结果

```bash
$ ./build/halibut --version
Halibut, version 1.3

# Smoke test: 生成 HTML 文档
$ echo '\C{test} Hello World' > $TMPDIR/test-halibut.but
$ ./build/halibut --html=$TMPDIR/test-halibut.html $TMPDIR/test-halibut.but
$ cat $TMPDIR/test-halibut.html
# → HTML 输出正常
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/halibut | 多格式文档生成工具 |
| share/doc/halibut/ | HTML 格式用户手册 |
| share/info/halibut.info | Info 格式文档 |
| share/man/man1/halibut.1 | man 手册页 |

## 注意事项

- halibut 是命令行工具（非库），conanfile.py 中 `package_type = "application"`
- 已创建 `commands.json` 声明命令行工具
- CMake 4 兼容性需要 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 变量
- 首次运行需触发 HarmonyOS 安全弹窗确认

---

**编译结束**: 2026-07-15 16:13
**最终状态**: built