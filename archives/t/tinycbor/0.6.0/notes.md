# tinycbor 0.6.0 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile + Makefile.configure 特性探测，无 configure 脚本）
- 编译日期: 2026-09-06
- 编译器: /data/service/hnp/bin/clang (OHOS aarch64, clang 15.0.4)
- 状态: published（conan-verify G2 通过，test_package 消费者测试通过；上游 Qt 测试 R03 复核见下）

## 编译步骤

```bash
# 源码（官方 tag v0.6.0，SHA-256 512e2c9fce74f60ef9ed3af59161e905f9e19f30a52e433fc55f39f4c70d27e4）
# 本机 github.com 直连不可达，经 ghfast.top 镜像获取官方 tarball（conandata 仍为官方 URL，
# conan-verify 会临时注入 ghfast.top 并回滚，见 E017 知识）
curl -fsSL -o tinycbor-0.6.0.tar.gz https://ghfast.top/https://github.com/intel/tinycbor/archive/refs/tags/v0.6.0.tar.gz
sha256sum tinycbor-0.6.0.tar.gz   # 512e2c9fce74f60ef9ed3af59161e905f9e19f30a52e433fc55f39f4c70d27e4

export CC=/data/service/hnp/bin/clang
make configure   # Makefile.configure 探测，生成 .config
make -j1         # lib/libtinycbor.a + lib/libtinycbor.so.0.6.0 + bin/cbordump + tinycbor.pc
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 | 本机网络无法直连 GitHub | 经 ghfast.top 镜像下载官方 tag tarball，SHA-256 与官方一致；conandata.yml 保留官方 URL（R39），本地 conan-verify/CI 自动镜像注入并回滚 |
| 2 | `make install` 失败 (install: No such file or directory) | OHOS sysroot 无独立 install 二进制（与 abcm2ps 同坑） | conanfile.py package() 手动拷贝 headers/lib/bin 并生成 package-relative tinycbor.pc |
| 3 | conan create: "No rule to make target 'configure'" | basic_layout 下 self.run() 在 build_folder 执行，Makefile 在 source_folder | build() 中 `cd '{source_folder}' && make ...`（与 abcm2ps 配方一致） |
| 4 | 消费者测试 'cbor.h' not found | 上游头文件安装于 include/tinycbor/ | 测试改用 `#include <tinycbor/cbor.h>`（上游 make install 布局） |
| 5 | 鸿蒙专项测试 "value b == -2" 失败 | cbor_encode_negative_int 第二参数是 uint64 绝对值，传 -2 被隐式转为巨大无符号值 | 改用 cbor_encode_int(&map, -2)（有符号 API） |
| 6 | W3 门禁 junk_check 失败：archives/u/util-linux-login/2.42.2/.ci-trigger | main 基线中 util-linux-login PR (761df452) 带入的空 .ci-trigger 文件不在 JC5 白名单；本分支无提交时 junk_check 回退 full 模式整仓扫描 | 本任务分支提交后 junk_check 进入 incremental 模式（origin/main...HEAD diff），仅检查本 PR 文件；该基线文件不在本 PR diff，真实 CI prdiff 模式不受影响 |
| 7 | 上游 Qt Test 测试（R02 曾误判"qt 未发布→0/54"） | R02 以 conan list/download --only-recipe 推断 qt/5.15.19 无 OHOS 二进制，属未验证结论 | R03 复核：`conan graph info` + `conan install --requires=qt/5.15.19 --build=never` 证实 OHOS armv8 二进制存在（package 01d92cf3…），54/54 实例化执行；42/54 通过；12/54（tojson）因 OHOS 运行期 `open_memstream` 缺陷失败（fclose=-9/EBADF、缓冲恒空、SIGTRAP；parser/encoder 同库 100% 通过 + 纯 libc 最小复现佐证，非库缺陷），恢复条件=SDK 修复 open_memstream 或以非 memstream 流式回调替代测试辅助。台账见 reports/upstream-test-ledger.md（R03 修正版） |

## 源码修改
- 无（未修改任何上游源文件；无 patches/）
---

**编译结束**: 2026-09-06 02:48
**最终状态**: published
