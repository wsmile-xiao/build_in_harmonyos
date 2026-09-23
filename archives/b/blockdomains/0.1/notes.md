# blockdomains 0.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，内嵌 dpkg-buildflags，recipe 绕过 make）
- 首次探针编译: 2026-09-05；权威 CI 全量通过: 2026-09-13
- 编译器: clang（OHOS SDK，aarch64-linux-ohos）
- 状态: built（权威 CI 全 PASS：L0 门禁、conan create + test_package 6 断言、L1/L2/L4/L5 全部通过）

## 上游与源码
- 上游仓库: https://git.rrq.au/rrq/blockdomains.git
- 构建归档: Debian 官方 `blockdomains_0.1.orig.tar.gz`（9641 字节，SHA256 固定于 conandata.yml）
- 内容: src/blockdomains.c(338行)/cache.c(73行)/database.c(248行) + blockdomainsctl(POSIX sh) + init 脚本 + asciidoctor man 页源

## 编译步骤（recipe 流程）

1. 下载源码并解包（conan `get()`）
2. 应用补丁 0001/0002
3. 绕过上游 Makefile（内嵌 `dpkg-buildflags`，Debian 专用，OHOS 不可用），直接用工具链 clang 编译 `src/` 三个源文件（include/lib 路径由 `conanfile.py` 的 `_deps_env()` 收集直接+传递依赖）
4. 链接 `-lnetfilter_queue -lnfnetlink`（来自 conan 依赖 libdir；`libnetfilter_queue` 为静态库，需补 `-lnfnetlink` 解析其 `nfnl_*`/`nlif_*` 符号）
5. 安装: `bin/blockdomains`（守护进程）+ `bin/blockdomainsctl`（控制脚本），二者并入 bin/ 以满足 CI L2/L5 检查

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义 | HarmonyOS（musl + Linux uapi 头）下 `<linux/netfilter.h>` 经 `<linux/in.h>` 拉入 `<linux/socket.h>`，与 `<netinet/in.h>` 先行引入的 `<sys/socket.h>` 冲突；libnetfilter_queue 头文件链经 `<linux/netlink.h>` 亦属同类机制（该链在本库编译全程未触发冲突，未单独验证） | 补丁 0001：在首个 Linux uapi 网络头前 `#define _UAPI_LINUX_SOCKET_H` 跳过 `<linux/socket.h>`，并补充 `typedef unsigned short __kernel_sa_family_t`（同 babeld 1.13.1 先例） |
| 2 | `__compar_fn_t` 未定义（database.c:193） | musl 不提供 glibc 内部 typedef `__compar_fn_t`，`end_domain_database_loading()` 的 qsort 比较器 cast 失败 | 补丁 0002：非 `__GLIBC__` 下条件 `typedef int (*__compar_fn_t)(const void *, const void *)` |
| 3 | 上游 Makefile 不可用 | 目标规则内嵌 `dpkg-buildflags --get ...`（Debian 专用） | recipe 绕过 make，直接 clang 编译三源文件 |
| 4 | `make install` 不可用 | install 目标依赖 asciidoctor 生成 man 页 | package() 手动安装二进制与 ctl 脚本，不装 man 页 |
| 5 | 依赖缺口（初期阻塞项，已解除） | 首个候选提交时 `libnetfilter_queue` 未入档未发布，CI L0i (R36) 阻塞构建图解析 | `libnetfilter_queue/1.0.5` 后已入档（archives/l/libnetfilter_queue）并发布到制品仓；最终候选 CI L0i (R36) 通过，构建图正常解析 |
| 6 | CI 第 2 轮 conan create 编译失败：`libnfnetlink/libnfnetlink.h` not found | 编译命令只含直接依赖的 `-I`，漏传递依赖 include 路径 | `conanfile.py` 的 `_deps_env()` 改为遍历 `self.dependencies.values()`，收集全部直接+传递依赖的 include/lib 目录 |
| 7 | CI 第 3 轮链接失败：对象文件不存在 | 编译产物名 `*.c.o` 与链接行 `*.o` 不一致 | `conanfile.py` 链接命令对象名改为与编译循环一致 |
| 8 | CI 第 4 轮链接失败：15 个 `nfnl_*`/`nlif_*` undefined symbol | `libnetfilter_queue` 为静态库，其依赖 `libnfnetlink` 的符号未解析 | 链接行在 `-lnetfilter_queue` 后追加 `-lnfnetlink` |

## 源码修改

- `patches/0001-harmoneyos-fix-sockaddr-storage-redefinition.patch`
  - 文件: `src/blockdomains.c`
  - 修改: 在 `#include <linux/netfilter.h>` 之前插入 `_UAPI_LINUX_SOCKET_H` 守卫与 `__kernel_sa_family_t` typedef
- `patches/0002-harmoneyos-provide-compar-fn-t-for-musl.patch`
  - 文件: `src/database.c`
  - 修改: include 块后条件提供 `__compar_fn_t` typedef

## 设备端验证（探针）

在设备上以 SDK clang（-Wall，SDK sysroot）对补丁前后各做过一次探针编译：

- 未打补丁: `src/blockdomains.c` 报 `error: redefinition of 'sockaddr_storage'`（linux/socket.h vs sys/socket.h）；`src/database.c` 报 `use of undeclared identifier '__compar_fn_t'`
- 打补丁后: 三个源文件全部编译通过；以本地 stub 实现替代 `nfq_*` 符号完成链接，产出的可执行文件在设备上运行，输出 `blockdomains opens library handle` → `blockdomains error during nfq_open()` 并以退出码 1 退出（设备无内核 NFQUEUE 时属预期干净失败），证明补丁、启动路径与动态链接均正常

（探针 stub 仅用于验证，不入档、不随包发布）

## 依赖版本

- libnetfilter_queue/1.0.5（netfilter.org 当前上游稳定版；已入档并发布，CI L0i R36 通过）
- libmnl、libnfnetlink（libnetfilter_queue 的传递依赖，经其 recipe 拉入，均已入档）
- 运行时仅依赖 libc.so；功能运行另需内核 NFQUEUE 与 iptables（NFQUEUE target）

## 上游测试

上游无自动化测试套件（NO_UPSTREAM_TESTS），已检查入口与证据：

- Makefile 目标: 仅 `default`（blockdomains + man 页）、`install`、`clean`，无 check/test 目标
- 源码树: 无 test/、tests/、*test* 文件（tarball 清单核对）
- README.adoc: 仅 Build/Install/Setup/Running 章节，无测试章节
- Debian 包: `blockdomains_0.1-1.debian.tar.xz` 内容仅 debian/{changelog,control,copyright,gbp.conf,rules,source/format}，无 debian/tests；Build-Depends 亦无测试相关包
- 结论: NO_UPSTREAM_TESTS；以 test_package 冒烟（构建级+功能路径级）替代

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方，绕过 make 直接 clang 编译 |
| conandata.yml | 源码 URL + SHA256 + 补丁引用 |
| manifest.yaml | 版本级 manifest（status: built，权威 CI 全 PASS） |
| notes.md | 本笔记 |
| patches/0001-harmoneyos-fix-sockaddr-storage-redefinition.patch | sockaddr_storage 冲突修复 |
| patches/0002-harmoneyos-provide-compar-fn-t-for-musl.patch | musl __compar_fn_t 修复 |
| test_package/conanfile.py | 测试包 |
| test_package/MANIFEST.yml | 上游测试声明（upstream_tests: []） |
| test_package/test_blockdomains.sh | 冒烟测试（6 断言） |

## 注意事项

- **候选已通过权威 CI（2026-09-13，全 PASS）**：L0 门禁（含 L0i R36 依赖发布检查、L0j/L0k/L0m）、知识库/杂项门禁（KC/JC）、conan create + test_package（6 断言全 PASS，含无内核 NFQUEUE 时 nfq_open 预期干净退出）、L1/L1a-c/L1e 负性破坏测试、L2/L4/L5 全部通过；L2 中 `blockdomains --version/--help` 为非阻塞警告（无内核 NFQUEUE 时程序退出码 1，属预期），`blockdomainsctl --version` OK
- 联调测试需 root + 内核 NFQUEUE + iptables：`blockdomainsctl start`（设备 CI 冒烟不依赖 root，见 test_blockdomains.sh）
- 编译完成后如需 `checksec`/L4 扫描，二进制默认继承工具链 flags（conanbuild env）

---

**编译结束**: 2026-09-13（权威 CI 全 PASS；首次探针 2026-09-05）
**最终状态**: built（初期依赖缺口已解除；recipe 与补丁经设备探针 + 设备权威 CI 双重验证）
