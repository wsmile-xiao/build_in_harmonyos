# dnsdbq 2.6.8 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure；init-build 误判 autotools，实际为 raw make）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS SDK，默认 target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 源码下载（github.com 直连超时，经 codeload/ghfast 镜像取官方 tag 归档，
# 与 github.com/dnsdb/dnsdbq/archive/refs/tags/v2.6.8.tar.gz 逐字节一致）
# sha256: 61e6dd22d258e67e6e87f2c7e4ba13a77ea519e7a6e521274016f17a2bc0f76e

# 依赖安装（jansson/curl 已发布至 ohpcd，预编译二进制，OHOS profile）
conan install --requires=jansson/2.15.1.1 --requires=curl/8.15.0.1 \
  -r=ohpcd --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 手工编译验证（JANSBASE/CURLINCL/CURLLIBS 注入依赖路径）
make CC="/data/service/hnp/bin/clang" JANSBASE=<jansson pkg> \
  CURLINCL="-I<curl pkg>/include" CURLLIBS="-L<curl pkg>/lib -lcurl"

# 配方生成与验证
ohc-run.py conan-init dnsdbq 2.6.8
ohc-run.py conan-verify dnsdbq 2.6.8   # G1-G4 + L2/L4/L5 全部通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | asinfo.c 编译失败：`_res`/`res_ninit`/`res_nquery`/`res_nclose` 未声明 | 原代码依赖 BIND 风格线程安全解析器 API（res_n*() 族与全局 `_res`），经典 POSIX 解析器接口（res_init()/res_query()）即可满足查询需求 | 补丁 0001：统一改用经典 POSIX 解析器接口 `res_init()`/`res_query()`，错误码经 `h_errno` 暴露（配 `hstrerror()`）；删除 `res_n*()` 族与全局 `_res` 的依赖，不持有 per-call resolver 状态。任何平台均走同一代码路径，无平台条件编译分支 |
| 2 | Makefile install 目标硬编码 /usr/local，无写权限 | 上游 install 写死 /usr/local/bin 与 /usr/local/share/man | 配方 package() 手工复制 bin/dnsdbq 与 man 页（bti/acedb 同法） |
| 3 | init-build 判定 build_system=autotools | URL 猜测逻辑对纯 Makefile 项目不识别 | conan-init 生成 autotools 模板后整体重写为 raw makefile 配方（JANSBASE/CURLINCL/CURLLIBS 变量注入） |
| 4 | github.com 直连超时，源码无法下载 | 本机网络到 github.com 主站超时（api/codeload/ghfast 可达） | 下载阶段经 codeload/ghfast 镜像通道取得官方 tag 归档（sha256 与官方一致）；conandata.yml `sources.url` 只保留官方 tag 归档 URL，不在配方内写入手工镜像前缀（r05 复核确认） |
| 5 | conan create 时 test_package 断言失败 | 初版断言 grep "Usage"（实际输出小写 "usage:"）且 --version 长选项不被支持 | test_package 断言改为 `-h | grep -qi usage` 与 `-h | grep -q '\-p dns|json|csv'`（R34 实质执行被测二进制） |
| 6 | r02 评审发现恒真空壳测试 | r01 交付的 test.c（print-only）与 CMakeLists.txt（add_test）不执行被测包也能通过 | r02 删除 test.c 与 CMakeLists.txt，断言移入 test.sh：实际执行包内 bin/dnsdbq 并断言 `-h` 输出（usage 行 + `-p dns\|json\|csv` 选项表），包损坏时测试必然失败（已实证反证） |
| 7 | /tmp 只读且 100% 满 | 系统 /tmp 挂载只读 | 全部构建临时文件使用 $TMPDIR=/storage/Users/currentUser/tmp |

## 源码修改

- `patches/0001-asinfo.c.patch`：统一经典 POSIX 解析器接口适配。asinfo.c 三处解析器调用（asinfo_domain_exists / asinfo_shutdown / asinfo_from_dns）统一改用 `res_init()`/`res_query()` + `h_errno`（配 `hstrerror()`）；删除 `res_ninit`/`res_nquery`/`res_nclose` 调用、全局 `_res` 引用与 per-call `static struct __res_state` 状态。**补丁内不含任何平台条件编译宏，任何平台均走同一代码路径**。

## 依赖版本

- jansson/2.15.1.1（ohpcd 已发布，预编译二进制）
- curl/8.15.0.1（ohpcd 已发布，预编译二进制）
- libresolv（OHOS sysroot 系统库 libresolv.a，非 conan 依赖）

## 验证结果

### 上游测试清点（R51 申报表）

dnsdbq 2.6.8 上游**没有任何测试套件**：
- 源码根目录无 tests/ test/ 目录（tar 包解包后 `find . -maxdepth 2 -type d` 仅顶层）
- Makefile 无 check/test/tests 目标（`grep -nE '^(check|test|tests):'` 无输出）
- 属纯命令行工具（仅发布 dnsdbq 二进制与 man 页），上游无可运行测试

### test_package 消费者测试（鸿蒙特有，R34 实质执行被测二进制）

```bash
# test.sh 实际执行包内 bin/dnsdbq（r03 复验实测输出）
sh test.sh <pkg>/bin/dnsdbq
# [PASS] T1: -h 输出 usage 行
# [PASS] T2: -h 列出 -p dns|json|csv 输出格式选项
# checked=2 passed=2
```

- 包损坏失败反证（r03 复验）：断言指向不存在二进制路径退出码 1；临时改名被测二进制退出码 1；现场恢复后复跑 T1/T2 退出码 0

### HarmonyOS 专项验证（本机 aarch64 直跑产物）

```bash
$ dnsdbq -h   # 输出 usage: dnsdbq [-acdfGghIjmqSsUv468] [-p dns|json|csv|minimal] ...（EXIT=0）
$ file dnsdbq # ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
$ readelf -d  # NEEDED: libcurl.so / libjansson.so / libc.so
```

- conan-verify 全门禁：G1 PASS / G2 PASS（conan create 干净构建）/ G3 PASS / G4 PASS + L2/L4/L5
- 统一经典解析器路径实测：与 asinfo.c 同调用序列（res_init/res_query/h_errno/hstrerror）的探针在 OH 工具链编译+链接+运行成功，res_query 实测返回真实 DNS 响应

## 交付物

| 文件 | 说明 |
|------|------|
| archives/d/dnsdbq/2.6.8/conanfile.py | raw Makefile CLI 配方（jansson/curl 依赖注入） |
| archives/d/dnsdbq/2.6.8/conandata.yml | 官方 tag 归档 + sha256 + 补丁声明 |
| archives/d/dnsdbq/2.6.8/patches/0001-asinfo.c.patch | 统一经典 POSIX 解析器接口适配（无平台宏） |
| archives/d/dnsdbq/2.6.8/test_package/test.sh | R34 实际执行 bin/dnsdbq 的可失败断言（r02 新增） |
| archives/d/dnsdbq/2.6.8/test_package/conanfile.py | 调用 test.sh 的 test_package 入口 |
| archives/d/dnsdbq/2.6.8/test_package/MANIFEST.yml | 上游测试清点 + 消费者断言声明（与 test.sh 一致） |
| archives/d/dnsdbq/commands.json | R38 CLI 工具声明 |
| archives/d/dnsdbq/2.6.8/manifest.yaml | 版本级 manifest |

> r01 交付的 `test_package/test.c` 与 `test_package/CMakeLists.txt`（恒真空壳，不执行被测包也能通过）已于 r02 删除，不再属于交付集；`test.sh` 为 r02 新增的实质断言文件。

## 注意事项

- 本机 github.com 主站不可达（api.github.com/codeload/ghfast 可达），下载走官方镜像通道
- /tmp 只读，构建临时目录一律用 $TMPDIR
- dnsdbq 只接受单字符短选项，不支持 GNU 长选项（--version 报 unrecognized option）
- 纯 Makefile 项目，conan-init 的 autotools 模板需整体重写
- 解析器适配为统一经典 POSIX 接口（res_init/res_query/h_errno），无平台条件编译分支（r02 评审 R8 修复，r03 复核维持）
---

**编译结束**: 2026-09-22 16:28
**最终状态**: built
