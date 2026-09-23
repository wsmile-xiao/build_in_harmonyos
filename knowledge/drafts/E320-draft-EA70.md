# E320: init-build 嵌套源码检测错误提升 Windows 专用子目录

## 错误模式
init-build 的嵌套源码检测逻辑在扫描源码目录时，发现 `external/source/byakugan/` 目录包含 `.cpp`/`.h` 等 C++ 源码文件，将其误判为"嵌套源码"并提升为主源码目录。但 byakugan 是 Windows 专用调试器扩展（使用 WinDbg API、Windows 头文件），不是项目的主源码。

## 影响
- 真正的 metasploit-framework 源码被 byakugan 的文件覆盖
- 构建上下文指向错误的源码目录
- 后续所有编译操作都在错误的源码上进行

## 解决方案
1. 重新下载并解压真正的源码 tarball 到 `.orig` 和 `.work` 目录
2. 不依赖 init-build 的嵌套检测逻辑
3. 手动创建或修复 `.build-context` 文件
4. 建议修复 init-build 脚本：添加 Windows 专用目录排除列表（byakugan, DLLHijackAuditKit, ReflectiveDLLInjection 等）

## 验证
```bash
# 验证源码是否正确
ls $BUILD_SRC_DIR/msfconsole && head -1 $BUILD_SRC_DIR/msfconsole
# 应输出: #!/usr/bin/env ruby
```
