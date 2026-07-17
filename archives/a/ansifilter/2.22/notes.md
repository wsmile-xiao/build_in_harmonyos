# ansifilter 2.22 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-14
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

```bash
# 下载源码
git clone from GitLab tag 2.22

# 编译 CLI 工具
make -C src -f makefile -j1 CXX=clang++ CXXFLAGS="-Wall -O2 -DNDEBUG -std=c++17 -fPIC -D_FILE_OFFSET_BITS=64"

# 安装
cp src/ansifilter $TEST_PREFIX/bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 环境缺少 rm/cp/mv 等基础命令 | 鸿蒙 HP 环境使用 busybox 提供基础工具 | 使用 /data/service/hnp/bin/busybox 提供基础文件操作 |
| 2 | conan-init 生成错误 package_type = "library" | 自动检测将 Makefile 项目误判为 autotools 库 | 手动修正为 package_type = "application"，重写 build() 使用原生 Makefile |
| 3 | conan 配方中 copy() 路径保留问题 | conan.tools.files.copy() 默认 keep_path=True | 设置 keep_path=False，并调整 src 参数指向具体子目录 |
| 4 | 知识图谱错误命中 E099 (Boost b2) 和 E165 (shebang) | 引擎误匹配关键字 | 属于误报，不影响实际编译 |

## 源码修改
无补丁。源码未经修改直接编译通过。

## 依赖版本
- 无外部依赖（仅 C++17 标准库和 clang 编译器）

## 验证结果

```bash
$ ansifilter --version
ansifilter version 2.22
Copyright (C) 2007-2025 Andre Simon

$ ansifilter --help
# 完整显示所有选项（文本/HTML/LaTeX/RTF/SVG/BBCode 输出格式）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| archives/a/ansifilter/2.22/conanfile.py | - | Conan 配方 |
| archives/a/ansifilter/2.22/conandata.yml | - | 源码声明 |
| archives/a/ansifilter/2.22/test_package/ | - | 消费者测试 |
| archives/a/ansifilter/commands.json | - | 命令行工具声明 (R38) |
| test-install-ansifilter-2.22/bin/ansifilter | 269 KB | 编译的二进制 |

## 注意事项
- ansifilter 使用纯 Makefile 构建（无 autotools configure），因此 G0 clean-verify 的 configure 步骤不适用
- 项目包含可选的 Qt GUI 和 TCL 扩展，但 CLI 工具可独立编译，本次仅编译 CLI
- CI 上传前需确保 `zsh` 环境可用（本地 finish 因 zsh 不可用而中断，CI worker 上有完整环境）
---

**编译结束**: 2026-07-14 19:32
**最终状态**: built
---

**编译结束**: 2026-07-14 19:45
**最终状态**: built
