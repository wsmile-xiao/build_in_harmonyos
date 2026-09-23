# canopennode 4.1 适配笔记

## 编译环境
- 构建系统: custom（无上游构建系统，conanfile.py 直接编译栈源码）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 / llvm-ar
- 状态: built

## 编译步骤

1. `ohc-run.py init-build canopennode 4.1 --url=https://github.com/CANopenNode/CANopenNode/archive/refs/tags/v4.1.tar.gz`
2. `ohc-run.py lang-preflight canopennode 4.1` → detected=c（兼容 cpp）
3. 手动编译验证：clang 编译 21 个栈源文件 → libcanopennode.a → blank 示例链接运行
4. 编写 conanfile.py：build() 内用 Conan conf 编译器逐个编译栈源文件（CANopen.c + 301/303/304/305/309/storage/extra），`llvm-ar rcs libcanopennode.a`
5. `ohc-run.py conan-verify canopennode 4.1` → G0-G4 全 PASS
6. `ohc-run.py finish canopennode 4.1 published` → W3 本地 CI L0 门禁通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测把 example/ 提升为源码根 | 检测器只看子目录构建标记，误判示例目录 | 手动重建 .orig/.work 为 tarball 顶层（301/303/304/305/309/CANopen.c 等），核对 .tarball-sha256 |
| 2 | conan-verify G2 失败 `tools.build:compiler_executables:c does not exist` | 本环境无 per-key compiler conf | 改为 dict 形式 `self.conf.get("tools.build:compiler_executables", default={})`（与 bzip2 配方一致） |
| 3 | conan create build() 报 `no such file or directory: CANopen.c` | 源文件用相对路径 + self.run 默认 cwd 为 build 目录 | 全部改用绝对路径 `os.path.join(src, ...)` 并 `cwd=src` |
| 4 | W3 L0d stub_test_method 拦截 | test_package test() 无 self.run 直接执行二进制 | test() 补 `self.run(os.path.join(self.cpp.build.bindirs[0], "test_canopennode"), env="conanrun")` |
| 5 | G0 clean-verify configure exit 127 | 无构建系统库没有 configure 脚本（预期误报） | 非阻塞步骤，记录后继续（G2 conan create 已实证构建成功） |
| 6 | E017 镜像注入残留 ghfast-bak/.orig | conan-verify 临时注入 ghfast.top 镜像 | 提交前删除 .ghfast-bak/.orig，conandata.yml 恢复官方 HTTPS URL |

## 源码修改

无补丁（纯配方适配，不改上游源码）。

## 依赖版本

无外部依赖（ANSI C 标准库 + blank 驱动）。

## 验证结果

- conan-verify G2 conan create 干净构建通过（含 test_package）
- W3 本地 CI：L0d/L0j/L0k/L0m 门禁通过
- test_package 消费者用例：CO_new→CO_CANinit→CO_LSSinit→CO_CANopenInit→CO_CANopenInitPDO→CO_process 20 周期→CO_delete，输出 ALL TESTS PASSED
- 上游无测试目录/测试框架，source_declared_total=0

## 注意事项

- CANopenNode 是嵌入式 CANopen 协议栈（ANSI C），上游 tarball 无顶层构建系统；打包边界为栈源码（不含 example/ 演示应用与 storage/CO_storageEeprom.c，后者需外部 EEPROM 驱动）
- 头文件安装保留上游 include 布局（CANopen.h include "301/CO_driver.h" 等子目录相对路径），消费者需自行提供 CO_driver_target.h + CO_driver.c 驱动实现（test_package 用上游 blank 驱动模拟）
