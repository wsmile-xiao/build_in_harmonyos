# boost-defaults 1.90.0.2 适配笔记（OHOS PC, aarch64）— requirements-only 元包

## 上游事实（联网核验 2026-09-05）

- boost-defaults 是 Debian 的"默认 Boost 版本"依赖元包：无源码/构建/测试，
  仅 debian/ 打包目录（control + 生成脚本 create-boost-defaults-control.py）。
- 上游 VCS: https://salsa.debian.org/debian/boost-defaults, tag debian/1.90.0.2。
- 版本语义：1.90.0.2 = boost 1.90.0 + defaults 打包第 2 次修订。
  changelog 1.90.0.2: "[2ba41e6] Remove libboost-system-dev from Provides"。
- sources.debian.org API 确认 sid/forky 当前版本 1.90.0.2+nmu1（nmu1 是
  非维护者上传；本配方取维护者版本 1.90.0.2，与任务指定版本号一致）。
- 官方 tarball SHA256（salsa archive tag debian/1.90.0.2）:
  f5ee472059846f8e446264ab25cafaf9e3d81374775fdc56c734ad2cdd769ec4
- 上游 license: Expat (MIT)；Homepage https://www.boost.org/。

## 本仓移植形态

- conanfile.py 为 requirements-only 元包（先例 archives/a/astromatic/1.3）：
  name=boost-defaults / version=1.90.0.2，package_type=unknown
  （Conan 2.29 无 meta-package 枚举），settings 含 os/compiler/build_type/arch
  （L0p 门禁要求）。
- requires boost/1.90.0（ohpcd 已发布；W0 已验证 recipe 可下载 + binary
  17.2MB 可安装）。对齐 Debian libboost-dev (default 1.90) 语义。
- cpp_info 组件 `boost_defaults`：requires=["boost::boost"]，把 boost 包的
  默认组件集（Boost::boost 头文件目标，传播 Boost::unit_test_framework
  编译库）映射进 boost-defaults 命名空间。find_package(Boost) 的组件解析
  语义仍由 boost/1.90.0 提供（cmake_file_name="Boost"）。
- 元包无 package() 产物 → cpp_info.includedirs 必须显式清空（[]），否则
  CMakeDeps 生成的组件目标会指向包内不存在的 include/ 路径导致
  "Imported target includes non-existent path" 配置失败。
- 无 build/source/package 方法；conandata.yml 记录 salsa 官方源 URL/SHA256
  （配方不下载，供 CI source_trace 审计；predl 预下载失败不致命）。
- 无 commands.json（元包无二进制；L0k 判定为库型不要求）。

## 测试语义

- 上游无任何测试（元包，无 autopkgtest/make check）。
- test_package 消费者测试（CMake + Boost.Test）验证元包传播语义：
  1. <boost/smart_ptr/shared_ptr.hpp> / <boost/config.hpp> / <boost/version.hpp>
     等 Boost 头文件经 boost-defaults requires 传播可用；
  2. BOOST_LIB_VERSION == "1_90" / BOOST_VERSION == 109000（默认版本断言——
     元包存在意义就是把默认版本钉在 1.90）；
  3. boost-defaults::boost_defaults 元组件目标可链接（CMakeDeps，
     需 find_package(boost-defaults) 显式触发组件目标创建）；
  4. Boost::unit_test_framework 编译库真实链接 + 运行 3 个测试用例全过。
- 运行时环境：OHOS 加载器需定位系统 libc++_shared.so（/system/lib64），
  test() 在命令前缀注入 LD_LIBRARY_PATH（先例 archives/b/barvinok/0.41.9）。
- Boost.Test 静态库以 BOOST_TEST_ALTERNATIVE_INIT_API 编译 → 消费者测试
  必须提供 init_unit_test() 入口（与 boost/1.90.0 本体 test_package 同款）。
- 统计口径：test_package 断言数（assertion_count=8：3 个用例共 8 处断言）。

## W3 验证结果（2026-09-05）

```bash
conan create archives/b/boost-defaults/1.90.0.2 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → boost-defaults/1.90.0.2 Package created
# → test_package: Running 3 test cases... *** No errors detected
# → finish step [5/10] W3 本地 CI 模拟: Pass rate 100.0% (1/1)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMakeDeps 组件目标 not found | package_type=unknown 的包组件目标需 find_package(boost-defaults) 显式触发创建 | test_package CMakeLists 增加 find_package(boost-defaults REQUIRED) |
| 2 | Imported target includes non-existent path | 元包无 package() 产物，默认 includedirs=["include"] 指向不存在目录 | package_info 显式清空 includedirs/libdirs/bindirs |
| 3 | undefined symbol: init_unit_test() | boost/1.90.0 Boost.Test 用 ALTERNATIVE_INIT_API 编译，main 由库提供 | 消费者提供 init_unit_test() 注册测试（对齐 boost 本体测试写法） |
| 4 | Error loading shared library libc++_shared.so | conanrun 环境不含 OHOS 系统库路径 | test() 命令前缀注入 LD_LIBRARY_PATH=/system/lib64 |
| 5 | weak_ptr undefined template | 只 include shared_ptr.hpp 时 weak_ptr 仅前向声明 | 显式 include <boost/smart_ptr/weak_ptr.hpp> |

## OHOS 要点

- 元包无编译，无 OHOS 补丁；风险主要在依赖闭包（boost/1.90.0 已发布，
  W0 闭包完整）。
- 命名一致性：conanfile.name=boost-defaults 与目录 archives/b/boost-defaults
  一致（L0m-4）；分支 feat/boost-defaults-1.90.0.2 精确匹配（L0n）。
- 版本号 1.90.0.2 直接沿用上游 defaults 修订号（非 R37 适配后缀），
  制品仓无同版本占用（L0j 首发验证通过）。

## 参考

- 先例元包: archives/a/astromatic/1.3（requirements-only + conandata 审计源）
- 上游: https://sources.debian.org/src/boost-defaults/1.90.0.2%2Bnmu1/
- 本体: archives/b/boost/1.90.0（header-only + Boost.Test 静态库）
