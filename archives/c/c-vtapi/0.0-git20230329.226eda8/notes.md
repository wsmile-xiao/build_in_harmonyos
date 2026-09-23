# c-vtapi 0.0-git20230329.226eda8 适配笔记

## 编译环境
- 构建系统: autotools（git 快照无 configure，build() 先 autoreconf -fi 自举）
- 编译日期: 2026-09-06
- 编译器: clang 15（OHOS arm64, /data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

1. `autoreconf -fi`（源码树无 configure；tool_requires automake/1.18 + libtool/2.5.4）
2. `./configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos`
   （config.guess 无法识别 HarmonyOS，显式传 *-linux-ohos 三元组）
3. `make -j1`（E074: HMDFS jobserver fifo EPERM，禁用并行）
4. `conan create`（-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing）+ test_package 消费者编译与运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: ./confJkdcIa/subs1.awk: Permission denied（E114） | HMDFS 强制目录 setgid，configure 内 `umask 077 && mktemp -d` 生成不可写 drwx--S--- 临时目录 | build() 中 autoreconf 后移除生成的 configure 里的 umask 077（_drop_umask_077，同 abiword-plugin-clarisworks 方案） |
| 2 | 消费者编译 unknown type name 'pthread_mutex_t' | vtcapi_common.h 的 `#include <pthread.h>` 被上游注释（VtObject.h 的 VT_OBJECT_COMMON 宏直接使用该类型） | 0002-lib-vtcapi_common.h.patch 恢复 include |
| 3 | 消费者编译 unknown type name 'json_t' | VtResponse.h 使用 json_t 类型却未包含 `<jansson.h>` | 0001-lib-VtResponse.h.patch 增加 include |
| 4 | codeload URL 无扩展名 → conan get() BadZipFile | conan 按下载文件名扩展名推断压缩格式，commit hash 无扩展名被当 zip | conandata.yml sources 显式 `filename: c-vtapi-0.0-git20230329.226eda8.tar.gz`（E276） |
| 5 | github.com 主站 archive 端点间歇连接超时 | 本机网络至 github.com 主站不稳定 | conandata URL 用官方 codeload.github.com archive 端点（同一官方源、SHA-256 一致，R39） |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-lib-VtResponse.h.patch | VtResponse.h 增加 `#include <jansson.h>`，公共头自包含 |
| patches/0002-lib-vtcapi_common.h.patch | vtcapi_common.h 恢复非 Windows 下 `#include <pthread.h>` |

## 依赖版本

- curl/8.15.0（制品仓已发布）
- jansson/2.15.1.1（制品仓已发布）
- tool_requires: automake/1.18、libtool/2.5.4

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# EXIT 0；ctest 2/2 passed（test_c-vtapi 消费者 smoke + test_ohos HarmonyOS 专项，15 项检查离线真实 API）
# W3 本地 CI 模拟通过（.ci-result.json exit_code=0）
```

上游无独立测试用例（无 TESTS/make check 目标，8 个 examples 为需真实 API key 的样例程序），
双口径统计与枚举见 reports/test-ledger.md。

## 注意事项

- 上游公共头不自包含（pthread/json_t 缺 include）是上游遗留缺陷，已通过补丁在库侧修复，见知识草稿 E552。
- 制品仓 jansson/2.15.1.1 的 CMakeDeps 元数据未声明 includedirs，test_package 在 generate() 中显式注入其 include 目录（详见 test_package/conanfile.py 注释）。

**编译结束**: 2026-09-06 03:56
**最终状态**: built