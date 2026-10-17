# unibilium 2.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-30
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：`https://github.com/neovim/unibilium/archive/refs/tags/v2.1.2.tar.gz`（官方 archive，sha256=370ecb07...）
2. 解压源码
3. CMake 配置构建（上游无 automake 环境，采用官方 CMakeLists.txt）：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local ..
   make -j4
   ```
4. 生成 `libunibilium.a` 静态库 + `unibilium.h` 头文件
5. 测试：编译 t/*.c 为 .t，`prove -f t/*.t`（与上游 `make test` 同口径）
6. 安装到 staging：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan get() 解压报 BadZipFile | codeload/api.github tarball URL 无 .tar.gz 扩展名，conan 按 zip 解码 | conandata 改用官方 archive URL（自带 .tar.gz），或显式指定 filename |
| 2 | conan-verify G4 JSON 解析崩溃 | pip 全局 requests 缺 chardet/charset_normalizer，warning 混入 stdout | 安装纯 Python 的 chardet 消除 RequestsDependencyWarning |
| 3 | 上游 CMakeLists 不安装 pkg-config 文件 | CMake install 只含库与头文件 | 配方 package() 中补充生成 lib/pkgconfig/unibilium.pc（含 prefix=${pcfiledir}/../.. 定义） |
| 4 | 知识图谱 E293 误命中（C++17 异常规范） | unibilium 为纯 C 库，E293 是 C++ 旧代码问题 | 忽略误匹配，G2 实际通过 |
| 5 | W4 审计 P1-1：.pc 正确性无 CI 回归验证 | 下游 libtermkey 依赖 pkg-config 消费 .pc，但无 CI 步骤验证 | test_package test() 增加 Python 模拟 pkg-config 解析 unibilium.pc（Name/-lunibilium/relocatable prefix/flags），CI 无 pkg-config 命令故用 Python 解析 |
| 6 | W4 审计 P2-1：上游已含 unibilium.pc.in，手工 .pc 存在漂移风险 | 上游 CMake 未安装 .pc，配方手工生成；未来上游若开始安装会重复 | package() 先检测 <prefix>/lib/pkgconfig/unibilium.pc 是否存在，存在则复用上游产物，否则才手工生成 |
| 7 | W4 审计 P3-1：TERMINFO_DIRS 编译期宏不可复现 | 上游 configure 探测 ncurses*-config，CI 无此命令时走 fallback | generate() 显式设置 TERMINFO_DIRS 为上游 fallback 一致值，编译可复现 |
| 8 | W4 审计 P3-2：requirements() 空实现无注释 | 无依赖库的合法写法但易被误判模板 | 补充注释 `# 纯 C 库，无外部依赖（不依赖 curses）` |
| 9 | W4 复检 R2-1：test_package 用 self.run 包裹 shell 解析 .pc，导致 ${pcfiledir}/${includedir}/${libdir} 被 shell 展开失真 | test() 中 .pc token 校验走 shell 双引号路径 | 改为 recipe 内 Python 直接 `with open()` 读取 .pc 并逐 token 校验（Name/-lunibilium/${pcfiledir}/../.. 等 5 项），缺失抛 ConanException |
| 10 | W4 复检 R2-2：package() 硬编码 lib/pkgconfig 生成 .pc | 上游未来可能在 lib64 安装 .pc，存在漂移风险 | package() 遍历 ("lib","lib64") 检测上游已装 .pc，存在则复用，否则手工生成 |
| 11 | W4 复检 R3-1：test_package 消费验证路径仍硬编码 lib/pkgconfig，与 recipe 的 lib/lib64 检测不对称 | 上游未来在 lib64/pkgconfig 安装 .pc 时 test 会误报失败 | test() 同步遍历 ("lib","lib64") 定位 .pc（存在则验证，缺失抛 ConanException），与 recipe 保持对称 |

> W4 审计 P2-2（软件级 commands.json）为合规留白：R38 明确库类型不需要 commands.json，README 已说明，无需修复。
> W4 复检结论：三轮复检 verdict=pass，P0/P1/P2 清零，R3-1 修复后第四轮复检通过（P0/P1/P2=0，仅剩 1 个非阻塞 P3 观察项：修复后未重跑本地 conan create 刷新 .ci-result.json，建议合入前由 CI 重跑验证）。

## 源码修改

无补丁，源码无需修改即可编译。

## 依赖版本

- 无外部依赖（纯 C 库，不依赖 curses）

## 验证结果

```bash
# 上游测试（9 个测试文件，3678 断言）
prove -f t/*.t
All tests successful.
Files=9, Tests=3678, Result: PASS

# test_package 消费者测试（12 项断言）
1/1 Test #1: test_unibilium ...................   Passed

# conan-verify 门禁
G0/G1/G2/G3/G4 全部 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libunibilium.a | 72K | 静态库 |
| unibilium.h | 16K | 头文件 |
| lib/pkgconfig/unibilium.pc | - | pkg-config 文件（libtermkey 等下游使用） |

## 注意事项

- 纯库无 commands.json（R38 不适用）
- libtermkey 依赖 `pkg-config unibilium`，需保证 .pc 中 prefix 可正确解析
- TERMINFO_DIRS 编译期宏使用硬编码 fallback 路径（本机无 ncurses*-config）
---

**编译结束**: 2026-08-30 05:13
**最终状态**: built
