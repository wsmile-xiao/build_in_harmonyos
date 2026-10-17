# pistache 0.4.26 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-11}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

## 上游测试套件执行记录（with_upstream_tests）

按上游 CI 口径复现（`linux.yaml`：`meson test -C build --verbose`，全量套件无子集筛选）。

**测试依赖就绪**（均来自 `ohpcd` 制品仓，不走 `subprojects/*.wrap` 联网回退）：
`gtest/1.17.0`、`gmock/1.17.0`、`curl/8.15.0`、`cpp-httplib/0.18.0`。依赖解析与下载全部成功。

**阻塞点**：Meson 配置阶段报
```
../tests/meson.build:6:17: ERROR: Dependency 'gtest' is required but not found.
```
上游该行是 `dependency('gtest', main: true, fallback: ['gtest', 'gtest_main_dep'])`，
`main: true` 需要 `gtest_main` 这一"主程序"变体。

**根因（设备实测，非推断）**：制品仓的 `gtest/1.17.0` 包实际**已包含**所需产物：
- `lib/libgtest.a`、`lib/libgtest_main.a`、`lib/libgmock.a`、`lib/libgmock_main.a`
- `lib/pkgconfig/gtest_main.pc`（上游自带的 pkg-config 元数据）
- `lib/cmake/`、`include/gtest/`、`include/gmock/`

但该配方的 `package_info` 只声明了 `cmake_file_name=gtest` / `cmake_target_name=gtest::gtest`，
未声明 `pkg_config_name`，也未暴露 `gtest_main` 组件；conan 在 generators 目录生成的配置名为
`gtest-config.cmake`（dash 形式），而 Meson 的 `dependency('gtest')` 走 CMake 时找
`gtestConfig.cmake`/`gtest::gtest_main`，走 pkg-config 时找 `gtest.pc`/`gtest_main.pc`
——两条路都看不到包里已有的那份。旁证：同一构建中 `RapidJSON` 与 `date` 均被找到，
说明 CMake 查找链路本身可用，问题局限于该依赖的 `main: true` 语义。

**结论**：属**打包元数据暴露不完整**（第三方包缺 `gtest_main` 组件/pkg-config 名），
不是移植缺陷。解除方式（择一，均需单独决定）：
1. 在 `archives/g/gtest/` 配方补 `gtest_main` 组件与 `pkg_config_name`，单独立项提 PR
   （改动他人配方，不能并入本 PR，否则破坏 W2 原子性）；
2. 在本配方内提供指向包内 `lib/pkgconfig` 的可见性垫片（局部、需在 PR 描述说明理由）；
3. 仅跑不依赖 `gtest_main` 的用例子集，其余按 §8.6 逐类归因。

**当前状态**：上游测试通过率**未取得**，不以任何形式估算或占位。已取得的是
test_package 消费者测试的真实结果（`checks=10 failed=0`）与八门禁全过。
