# pmailq 0.7 适配笔记

## 编译环境
- 构建系统: custom（纯 Python 脚本安装，无编译）
- 编译日期: 2026-10-12
- 编译器: 无（Python 3 脚本，仅 py_compile 语法校验）
- 状态: built

## 编译步骤

pmailq 是单文件 Python 3 脚本，无需 C/C++ 编译。上游 Makefile 仅用于 pod2man 生成 manpage。

```bash
python3 -m py_compile pmailq
# 打包：拷贝 pmailq 到 package_folder/bin/ 并加可执行位
# 文档：README.md、CHANGELOG、COPYING、AUTHORS、pmailq.pod 到 share/doc/pmailq/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试套件 | 0.7 源码树仅 AUTHORS/CHANGELOG/COPYING/Makefile/README.md/pmailq/pmailq.pod，无 tests 目录、无 check/test target | test_package 用 PATH 垫片伪造 postqueue/postsuper，喂真实 fixture 全链路验证 list/parse/del 与过滤器 |
| 2 | 运行时依赖 postfix | 脚本调用 `postqueue -p` / `postsuper -d`，OHOS/CI 无 postfix | 仅运行时可选依赖，不声明 Conan requires；测试用垫片覆盖 |
| 3 | 0.7 包内脚本 _VERSION 仍为 '0.6' | 上游 0.7 tag 只改文案未同步版本号常量 | --version 测试只断言非空退出码为 0，不硬编码版本号；notes 如实记录 |

## 源码修改

无补丁。脚本在 OHOS Python 3 下无需修改（仅用 argparse/fnmatch/subprocess/fcntl/select/re 标准库）。

## 依赖版本

无编译时依赖。运行时可选：postfix（提供 postqueue/postsuper）、python3。

## 验证结果

待 HMBS 真机预检回填（conan create 全流程 + test_package 13 项 + 上游 no_tests 审计标记）。

## 注意事项

- fcntl/select 为 Unix 专用，OHOS（类 Linux 内核）可用，Windows 本机不可直接跑功能测试。
- 不要把 manpage 生成（需 pod2man/perl）加入 build，避免引入多余工具链依赖。
