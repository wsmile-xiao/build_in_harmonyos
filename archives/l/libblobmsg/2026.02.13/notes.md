# libblobmsg 2026.02.13 适配笔记

## 上游信息

- 上游仓库：https://github.com/openwrt/libubox（官方镜像， canonical 为 git.openwrt.org/project/libubox.git）
- 上游版本：2026.02.13，对应 commit 1aa36ee774c8db4d7a396903e0d2e1fb79ee8bf1（OpenWrt 2026-02-13 更新，PKG_SOURCE_DATE=2026-02-13）
- 源码包：https://github.com/openwrt/libubox/archive/1aa36ee774c8db4d7a396903e0d2e1fb79ee8bf1.tar.gz
- sha256：350407e95f40d2b07f39668fa15af8487089b2b72ea80cb9af83e580a8825c71（本机实测下载 106895 字节计算）
- 许可证：ISC
- 构建系统：CMake（cmake_minimum_required 3.13）

## 与 libubox 的关系

- libblobmsg 并无独立上游仓库；它是 OpenWrt libubox 源码树中的 blobmsg 切片
  （blob.c/blobmsg.c 在 ubox 库，blobmsg_json.c 在 blobmsg_json 库）。
- 本配方与已发布的 libubox/20260222 同源不同版本（2026-02-13 vs 2026-02-22），
  配方结构直接复用 libubox/20260222 的验证结论。
- Alpine 同样把 libblobmsg 作为 libubox 的子包发布（libblobmsg 2026.02.13-r0，origin libubox）。

## 编译配置

- 依赖：json-c/0.18（ohpcd 制品仓已发布，上游 PKG_SEARCH_MODULE(JSONC json-c REQUIRED) 硬依赖）
- CMake 选项：-DBUILD_LUA=OFF（OHOS 无 lua，否则 SEND_ERROR）、-DBUILD_EXAMPLES=OFF
- OHOS 映射：CMAKE_SYSTEM_NAME=Linux（E092，无 OHOS 平台模块）
- PKG_CONFIG_PATH：CMakeToolchain 不注入，需在 build() 手动加入 generators_folder
- RPATH：CMAKE_SKIP_INSTALL_RPATH=TRUE，安装后用构建树 .so 覆盖（OHOS musl loader 无法加载被改写的 .so，与 libubox 相同平台问题）
- 纯库包：package() 删除 bin/ 与 share/（jshn CLI 与 sh 脚本不随本包发布），R38 库类型无 commands.json

## 产物

- lib/libubox.so（blobmsg 核心：blobmsg_buf_init/add_*/parse 实际落在此库）
- lib/libblobmsg_json.so（blobmsg<->json 转换）
- lib/libjson_script.so
- include/libubox/*.h（含 blob.h/blobmsg.h/blobmsg_json.h）
- package_info libs = ["ubox", "blobmsg_json", "json_script"]

## 上游测试

- 上游 tests/ 有 14 个 test-*.c（cram .t + shunit2 驱动，单元程序仅在
  UNIT_TESTING=ON 时构建且未注册为 ctest）。
- 配方 generate() 置 UNIT_TESTING=ON；build() 前按 OHOS 能力裁剪 tests/
  CMake 接线：禁用 *-san（需 address/leak sanitizer，OHOS clang 不支持）、
  cram 子目录（构建期 pip install cram 需联网）、shunit2 子目录、fuzz
  子目录（需 -fsanitize=fuzzer）与顶层 jshn-san。
- build() 内 _run_upstream_tests 真实执行全部 14 个二进制共 15 次调用
  （test-blob-parse 跑正/负向两个 fixture），每次调用按其 tests/cram/
  test_*.t 的期待输出片段做内容校验（非只看退出码；toybox 空 fixture
  教训：exit 0 的桩/空输出过不了片段匹配）。负向测试
  test-b64_decode/encode 仅当 abort 并打印上游期待的 Assertion 信息才计
  通过（与 .t 一致）。任一失败即抛异常使构建失败，不伪造通过。
-  verdict 经 print + self.output.info 双通道输出
  HMBS_UPSTREAM_TEST_RESULT（framework=custom-c-unit，discovered=15），
  并落盘 build/hmbs_upstream_result.json，由 package() 打进包内供
  test_package 在缓存命中轮次重发。
- test_package 的 test() 在消费者二进制 rc=0 后输出
  HMBS_TEST_PACKAGE_RESULT（discovered=13/passedCount=13，13 个 check()
  断言任一失败即 exit 1，故 rc 0 蕴含 13/13），再重发上游 verdict；
  verdict 缺失或非 passed 时直接失败。
- 待真机预检返回 conan create 日志后，如实摘录 15/15 与 13/13 填写
  PR 正文通过率。

## 验证

- 本轮仅完成未提交工作树，未在本机运行 conan（按任务守则，验证由 HMBS 真机预检完成）。
- 下一步等待 HMBS 真机 conan create 日志（编译 + build() 内 15 项上游调用 + test_package 13 断言），再据日志填 PR 通过率。

## 交付文件

- conanfile.py / conandata.yml / manifest.yaml / notes.md（本文件）
- test_package/conanfile.py / test.c / CMakeLists.txt / MANIFEST.yml
- 软件级 README.md（本包为纯库，无 commands.json）
