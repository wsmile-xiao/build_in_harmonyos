# giflib

## 简介
giflib — GIF 图像格式的读写库和工具集。提供 GIF 编码、解码、裁剪等操作。

## OHOS 适配
- 使用简单 Makefile，无 configure 脚本
- 从 Conan `tools.build:compiler_executables` 获取 clang 和 llvm-ar
- 通过 make 命令行注入 `-fPIC`，不修改上游构建 Makefile
- 为上游回归测试补充可移植的截断输入生成方式，以 `wc -c` 和 `dd` 等价替代 GNU `head --bytes=-20`
- 支持 Conan `shared=True/False`，包内仅包含 libgif、公开头文件和许可证
- 上游回归测试会构建所需 GIF 工具，但不把工具打入库包
- 消费者测试在编码/解码失败时从 `GifFileType::Error` 读取操作错误，并在关闭对象前记录，避免 open/close out-param 覆盖根因

## 依赖
- 编译依赖：无

## 功能验证
```bash
conan create archives/g/giflib/5.2.2 -o 'giflib/*:shared=True'
conan create archives/g/giflib/5.2.2 -o 'giflib/*:shared=False'
```

WSL Clang 15 近似验证中，上游 49/49 项行为检查及消费者 GIF 编码/解码往返测试均通过。首轮 HarmonyOS CI #7520 暴露了 `head` 命令差异，修复后的 Build #7543 已通过；后续 Review 的诊断修复仍以再次更新后的当前 HEAD CI 为准。

## 参考
- 官方网站：https://sourceforge.net/projects/giflib/
