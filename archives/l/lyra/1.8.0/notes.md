# lyra 1.8.0 适配笔记

## 编译环境
- 构建系统: header-only（上游 CMake INTERFACE / meson，本包无需编译，仅安装头文件）
- 编译日期: 2026-09-02
- 编译器: clang/clang++（OHOS arm64, clang 15.0.4）
- 状态: built

## 编译步骤

Lyra 是 header-only C++11 命令行解析库（bfgroup/Lyra）。无需 configure/make：
1. `cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local`（CMake INTERFACE 目标）
2. `cmake --build build` + `make install DESTDIR=$TEST_PREFIX` → staging 隔离安装 30 个头文件
3. 上游测试：`clang++ -std=c++11 -Iinclude -Iexamples tests/*_test.cpp` 批量编译并运行（conan build() 内集成）
4. staging 消费验证：以 staging include 编译 smoke.cpp 并运行 `-v hello` → `staging-ok v=hi`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 本机网络对 github.com 直连超时（E017） | 官方 tarball 预置于 TMPDIR/builds 后 init-build 复用；CI 侧由 E017 临时注入 ghfast.top 镜像 |
| 2 | conan-init 生成 autotools 模板 | 按 URL 猜测构建系统，header-only 库需人工改写 | 改写为 package_type=header-library 配方，补齐 export_sources()+apply_conandata_patches() |
| 3 | 上游 doc_* 测试找不到 example 源 | tests/*_run_test.cpp include examples/ 下的 doc_*.cpp | conan build() 编译上游测试时追加 `-I<src>/examples` |
| 4 | test_package smoke 解析失败 "Unable to convert" | lyra 1.8.0 中 bool opt 带 hint 会当作需值选项 | bool flag 写 `opt(verbose)["-v"]` 不带 hint |

## 源码修改

无补丁（纯 header-only 库，未改上游源码）。

## 依赖版本

- 无第三方运行时依赖（header-only，0 依赖）
- 构建依赖：clang 15.0.4（OHOS arm64）、cmake 4.1.2、conan 2.29.1

## 验证结果

```bash
# 上游测试（conan build() 内集成，日志见 reports/conan-create.log）
[lyra upstream tests] 58 passed / 0 failed
# conan-verify（G0-G4 + L2/L4/L5）
✅ 配方验证通过: lyra 1.8.0（可标记 status: published）
# test_package smoke
lyra smoke: name=hello verbose=1
OK: lyra headers + real lyra::cli usage works
```

## 注意事项

- lyra 为纯头文件 C++11 库：conan 配方 `package_type="header-library"`，`cpp_info.libs=[]`，仅安装 `include/lyra/`。
- bool 类型 opt 不要带 hint 参数（详见问题 #4）。
- 依赖项交付：PR-only，不创建 Issue。

**编译结束**: 2026-09-02
**最终状态**: built