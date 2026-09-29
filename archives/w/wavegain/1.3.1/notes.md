# wavegain 1.3.1 — notes (device verification log appended during build)

## 选库结论（§3.2）
1. 上游：MestreLion/wavegain（John Edwards 原作 fork），https://github.com/MestreLion/wavegain；1.3.1 tag（upstream/1.3.1）经 git ls-remote 实锤
2. 语言/构建生态：纯 C（9 个 .c），零外部依赖（FreeBSD port 声明 0 dependencies）；无 configure/Makefile（仅 Windows .sln/.vcproj），直接 $CC 编译
3. 上游无测试套件（无 testsuite/、无 make check，tag 树 25 文件实测确认）——R51 如实声明零上游用例 + test_package 真实 roundtrip（libexplain 先例口径）
4. main/制品双零（2026-09-28 实测）；任务 id=11814，分支 feat/wavegain-1.3.1
5. 可行性：高；难度 A

## 降级边界声明
- 只装 `install-bin` 等价（单 wavegain 二进制直接拷贝入 bin/）：无文档安装目标
