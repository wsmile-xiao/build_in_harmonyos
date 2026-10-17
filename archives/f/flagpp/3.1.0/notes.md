# flagpp 3.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE target，无编译产物）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++
- 环境: HarmonyOS HongMeng Kernel 1.12.0 aarch64（鸿蒙 PC 真机）
- 状态: built

## 编译步骤

1. `ohc-run.py init-build flagpp 3.1.0 --url=https://github.com/Curve/flagpp`（GitHub 直连超时，经 ghfast.top 镜像获取官方 v3.1.0 tag tarball，SHA-256 双镜像核对一致）
2. `lang-preflight`：detected=cpp，匹配通过
3. `cmake -Dflagpp_tests=ON -DCMAKE_CXX_STANDARD=23` → `cmake --build` → 上游测试二进制 `./tests/flagpp-tests`：18 断言全过
4. `cmake --install` 到 staging（test-install-flagpp-3.1.0）
5. `conan-init` 生成配方 → 重写为 header-only 配方（package_type='header-library'）
6. `conan-verify`：G0-G4 全 PASS（含 conan create + test_package 消费者测试）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 FAIL：conanfile.py 缺少 build() 方法 | header-only 无构建系统，模板缺 build() | 补显式 no-op build()（E257 等价命中） |
| 2 | conan create ERROR: Package type is 'library', but no 'shared' option declared | 模板 package_type='library' 缺 shared 选项契约 | 改为 package_type='header-library'（E283/E470 等价命中） |
| 3 | conan create 后 test_package 报 include 路径不存在 | package() 复制头文件目标路径基于相对 dst，产生空包 'No files in this package!' | copy 的 dst 改为基于 package_folder 的绝对路径（E311 + header-only copy 草稿等价命中） |

## 依赖版本

无第三方依赖（header-only 库，零 requires）。

## 验证结果

```bash
$ ./tests/flagpp-tests
Suite 'basic': all tests passed (18 asserts in 0 tests)
Suite 'wrapped': all tests passed (18 asserts in 0 tests)
Suite 'global': all tests passed (0 asserts in 0 tests)

$ clang++ -std=c++2b -I <include> test_package/test.cpp && ./test_flagpp
flagpp 3.1.0 consumer test: OK (bitwise ops on scoped enum)
```

## 注意事项

- flagpp 是 header-only C++23 库（scoped enum 位运算），运算符为全局模板，受 `flagpp::enabled<Enum>` 约束；test_package 消费者用非限定查找即可。
- 上游 CMake 通过 CPM 拉取 PackageProject/ut 依赖，本机依赖下载走镜像通道；Conan 配方不构建，只复制头文件，规避该依赖。
- W3 本地 CI 的 junk_check 全仓扫描会命中其他库（cloog/kics）main 上已提交的历史基线状态文件（`.build-closed`/`.staging-verified`），与本库无关；已按受限隔离→复验（W3 通过）→无条件恢复处理，详见最终回报审计。
