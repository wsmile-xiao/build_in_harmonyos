# fruit 3.7.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos, OHOS SDK）
- 状态: built

## 编译步骤

1. 官方源码：`https://github.com/google/fruit/archive/refs/tags/v3.7.1.tar.gz`
   SHA-256: `ed4c6b7ebfbf75e14a74e21eb74ce2703b8485bfc9e660b1c36fb7fe363172d0`
   （GitHub 直连不可达，经 gh-proxy 镜像下载，校验和一致；conandata 保留官方 URL 优先 + gh-proxy fallback）
2. 环境：Python 3.12.9 / Conan 2.29.1（OHOS 适配版）/ ohos-aarch64 profile（os=OHOS, arch=armv8, clang15, libc++17）
3. `conan create . --version=3.7.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...` 通过，
   消费者探针 + 鸿蒙专项测试编译链接运行通过（详见 reports/）
4. 上游测试：CMake Release 配置 + `python3 -m pytest` 全量运行 1201/1201 通过（详见 reports/test-ledger.md）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create `NotADirectoryError: .../build/Release` | 上游源码根目录含 Bazel `BUILD` 文件，与 CMake 构建目录 `build/` 在大小写不敏感文件系统（HMDFS）上冲突 | 配方 layout() 改用 `conan-build/` 构建目录，规避冲突 |
| 2 | `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.2)`，本机 CMake 4.1 移除 <3.5 兼容 | 配方 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` 注入 |
| 3 | `include conanbuildinfo.cmake / conan_basic_setup` 失败 | 上游在 `FRUIT_IS_BEING_BUILT_BY_CONAN=YES` 时走 Conan 1 集成，Conan 2 无此机制 | 不设该变量；Release 下 tests/examples 子目录加入但 ALL 默认只构建 libfruit |
| 4 | test_package 消费者编译 `allocating abstract class` | fruit 基于 typeid 做类型键，参与 DI 的类必须位于命名空间作用域；且抽象接口取用必须写 `injector.get<Greeter*>()`（带指针） | 调整测试写法：非匿名命名空间 + `get<Greeter*>()`（官方 hello_world 范式） |
| 5 | `NoBindingFoundError<GreeterImpl>` | fruit 要求实现类显式标注可注入构造函数（INJECT 宏），默认构造函数不被 bind<I,C> 自动识别 | 消费者实现类加 `INJECT(GreeterImpl()) = default;` |
| 6 | 鸿蒙专项测试 `NonConstBindingRequiredButConstBindingProvided` | `bindInstance(临时对象)` 退化为 const 绑定，而 `get<Value&>()` 需要非 const 绑定 | 改用具名左值 `static Value` 绑定（`bindInstance(C&)`） |
| 7 | GitHub 直连超时/不可达 | 执行环境无法直连 github.com | 下载经 gh-proxy 镜像（与 CI mirror fallback 同机制），conandata 官方 URL 优先 |

## 源码修改

无源码/补丁修改（patches/ 为空）：纯配方层适配（Conan 2 风格 conanfile.py + 布局/变量注入）。

## 依赖版本

无外部 Conan 依赖（`FRUIT_USES_BOOST=OFF` 使用 std::unordered_map/set，上游支持的配置）。

## 验证结果

```bash
# 库构建 + test_package 消费者/鸿蒙专项
conan create . --version=3.7.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # exit 0
# 上游 pytest 全量
python3 -m pytest -p no:cacheprovider -r a -q tests/test_*.py          # 1201/1201 pass
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方（CMake，FRUIT_USES_BOOST=OFF，静态库） |
| conandata.yml | 官方 URL + sha256 + gh-proxy fallback |
| test_package/ | 消费者探针 + 鸿蒙专项测试（真实 DI API 调用） |
| reports/ | conan-create.log / upstream-cmake-configure.log / upstream-make.log / upstream-pytest.log / test-ledger.md |

## 注意事项

- fruit 为库类型（libfruit.a），无 CLI 可执行产物，无需 commands.json（R38）。
- 静态构建（BUILD_SHARED_LIBS=OFF），非系统同名库，符合 R26 语义。
- upstream test 声明 336 个 def test_ 方法，参数化展开后 pytest 收集 1201 个实例，全部执行通过（双口径详见 test-ledger.md）。
---

**编译结束**: 2026-09-28 11:04
**最终状态**: built
