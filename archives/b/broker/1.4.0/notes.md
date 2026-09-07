# broker 1.4.0 适配笔记

## 编译环境
- 构建系统: cmake（上游默认：捆绑 CAF 子模块 add_subdirectory(caf)）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos）
- 状态: published

## W0 依赖预检（CAF 决策，附证据）

制品仓检查（conan download -r=ohpcd）：
- `actor-framework/0.17.6` 配方已发布（2026-08-10），但其 generate() 固定
  `CAF_NO_OPENSSL=ON`，package_info 仅暴露 core/io 组件（无 openssl/test），
  cmake_file_name=actor-framework（非 find_package(CAF) 所需的 CAFConfig）。
- broker 1.4.0 的 CMakeLists 在外部 CAF 模式（CAF_ROOT_DIR）要求
  `find_package(CAF COMPONENTS openssl test io core REQUIRED)`；无该变量时走
  `add_subdirectory(caf)` 捆绑构建（上游官方默认路径）。
- 树级验证：v1.4.0 的 .gitmodules 将 zeek/actor-framework @
  f7d4fc7ac679e18ba385f64434f8015c3cea9cb5 固定为 caf/ 子模块；将该 commit
  归档与上游 actor-framework **0.17.6** 发布 tarball 做 `diff -rq` =
  0 差异（内容逐字节一致，无需"fork 适配"）。
- 结论：不 requires actor-framework/0.17.6，采用上游默认捆绑构建。
  理由：①制品仓包缺 openssl/test 组件（broker 强依赖）；②捆绑内容是上游
  pin 的官方 CAF（==0.17.6 发布树）；③单 PR 单软件不引入跨包依赖（R36）。

## 源码结构

GitHub v1.4.0 tag tarball 不含子模块内容；conandata.yml 声明 4 个官方源：
broker tag + 3 个子模块 commit 归档（caf=zeek/actor-framework@f7d4fc7ac、
cmake=zeek/cmake@153496b 提供 CommonCMakeConfig.cmake、3rdparty=zeek-3rdparty
@bc5e6ab 提供 sqlite3 amalgamation 与 doctest.h）。sha256 下载核验一致。

## 关键配置（generate()）

- ENABLE_STATIC_ONLY=ON 且显式 CAF_BUILD_STATIC_ONLY=ON：broker 自身把
  ENABLE_STATIC_ONLY 映射成 CAF_BUILD_STATIC（会同时产出 .so），显式钉住
  static-only 保证产物零运行时动态库依赖。
- BROKER_DISABLE_TOOLS/DOCS=ON、DISABLE_PYTHON_BINDINGS=ON（OHOS 不打包
  python 绑定与 broker-node/pipe 工具）。
- OPENSSL_INCLUDE_DIR / OPENSSL_LIBRARIES / OPENSSL_ROOT_DIR 三连钉到 conan
  openssl/3.5.8.1（libcrypto.a 在 libssl.a 前）：本机 ~/.harmonybrew 宿主
  OpenSSL 会先被 find_package(OpenSSL)/CAF 的"parent 提供"逻辑命中（实测
  broker-test 链接 ~/.harmonybrew/lib/libssl.so 报未定义符号）。
- OHOS lld 运行时缺 libxml2.so.16：environment() 注入 SDK llvm/lib 到
  LD_LIBRARY_PATH（CI 实测 'Error loading shared library libxml2.so.16'）。
- 上游测试在 build() 中经 ctest 执行；TMPDIR 指向构建树内可写目录
  （OHOS 沙箱 /tmp 只读）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CAF 同时产出 .so+.a，broker-test 链接 .so 运行报 loader 错误 | 仅设 ENABLE_STATIC_ONLY 时 broker 映射为 CAF_BUILD_STATIC（非 STATIC_ONLY） | 显式 CAF_BUILD_STATIC_ONLY=ON |
| 2 | broker-test 链接期未定义 OPENSSL_* 符号 | find_package(OpenSSL) 命中宿主 ~/.harmonybrew（config-mode OpenSSLConfig 遮蔽 conan 包） | OPENSSL_LIBRARIES/INCLUDE_DIR/ROOT 钉 conan 包，crypto 在前 |
| 3 | 上游 generator_file_writer / backend 套件失败：Unable to create unique filename: Read-only file system | broker::detail::make_temp_file_name 硬编码 /tmp（OHOS 沙箱只读） | patches/0001：读 $TMPDIR 回退 /tmp（POSIX 通用修复，已 git apply 校验） |
| 4 | 消费者 burst 测试发布端阻塞 | publisher::publish 受流信用背压约束（有界在途窗口） | 分批发布（每批 10 条）+ 逐批消费，1000 条全量有序验证 |

## 补丁

- patches/0001-filesystem-honor-tmpdir.patch：make_temp_file_name 支持
  $TMPDIR 环境变量（默认仍 /tmp）；POSIX 通用可移植性修复，非平台宏。

## 依赖版本

- openssl/3.5.8.1（制品仓发布）
- CAF（捆绑）= actor-framework 0.17.6 内容（zeek pin f7d4fc7ac）

## 验证结果

- conan create：上游 C++ 套件 22/22 通过（backend core data data_generator
  generator_file_writer meta_command_writer meta_data_writer error filter
  integration master publisher publisher_id radix_tree ssl status
  status_subscriber store store_event subscriber topic zeek）
- 注意：上游 22 套件运行于 CAF test_multiplexer 假网络之上，不覆盖真实
  TCP；新增消费者测试以真实 127.0.0.1 loopback peer 连接补齐验证
- test_package 消费者测试 7/7（30 断言）通过
- 制品：libbroker.a + 捆绑 CAF 静态库（libcaf_{core,io,openssl}_static.a）
  + 头文件（include/broker、include/caf）+ 许可证

## 注意事项

- 上游 python 绑定/工具（broker-node/broker-pipe）未打包（库类型）
- 测试套件 ssl/integration 基于 test_multiplexer；真实网络行为由新增消费者
  用例覆盖（loopback 实测通过）
---

**编译结束**: 2026-09-05 12:33
**最终状态**: built
