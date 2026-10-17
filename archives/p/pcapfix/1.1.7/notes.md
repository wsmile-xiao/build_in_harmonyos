# pcapfix 1.1.7 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-18（前置适配阶段，本机未编译）
- 编译器: clang（配方从 `tools.build:compiler_executables` 获取）
- 状态: built（真机 conan create + test_package 全绿；待 CI/finish 后更新 published）

## 上游信息

- 官方仓库: https://github.com/Rup0rt/pcapfix （作者主页 https://f00l.de/pcapfix/）
- 源码: GitHub tag `v1.1.7` 归档，sha256
  `dcaf0e7104572f14b56ea3406663cedc5df7cf732af451adab02e523bc24905b`
  （2026-09-18 计算；tar 内 16 文件与 GitHub tag 内容逐文件核对，pcapfix.c 内
  `#define VERSION "1.1.7"` 一致）
- 许可证: GPL-3.0-or-later（COPYING 为 GPLv3 全文）
- 功能: 修复损坏的 pcap/pcapng 文件（扫描重建全局头、修正包头）
- 语言: C99（pcapfix.c/pcap.c/pcap_kuznet.c/pcapng.c + winfunc.c Windows 兼容层）

## W0 依赖发布检查

零依赖。源码全部 `#include` 为 libc 标准头（stdio/stdlib/string/unistd/fcntl/
getopt/inttypes/arpa/inet/libgen），Winsock.h 仅在 Windows 宏下生效。
无 conan `requires`，无需检查制品仓。

## 上游测试清点（R51）

上游 v1.1.7 发布包 16 个文件，Makefile 目标仅
`all/pcap/pcap_kuznet/pcapng/install/uninstall/clean`，**无 check/test 目标，
无 tests/ 目录，上游仓库无 CI**。清点证据见 tar 列表与 Makefile（源码核查于
2026-09-18）。因此上游测试通过率为 0/0（不适用）；test_package 自带功能测试
替代（见 test_package/MANIFEST.yml，9 个检查点）。

## 编译步骤（配方设计）

```sh
# 纯 Makefile，无 configure
make CC="<conan conf 编译器>" CFLAGS="-O2 -Wall -Wextra -std=gnu99 -pedantic -D_FORTIFY_SOURCE=2 -fstack-protector" -j1
# 不调用 make install（install -pDm 为 GNU coreutils 专属），package() 手动复制
# pcapfix → bin/，pcapfix.1 → share/man/man1/，COPYING → licenses/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认 CFLAGS 在 clang/OHOS 上有风险 | `--param=ssp-buffer-size=4` 为 gcc 专属（clang 拒绝未知 --param）；`$(shell getconf LFS_CFLAGS)` 依赖 getconf | 整体显式传 CFLAGS（make 命令行变量优先于 Makefile 内 `CFLAGS +=`，getconf 因此不再展开） |
| 2 | `make install` 不可移植 | `install -pDm755` 的 `-D` 为 GNU coreutils 专属，OHOS toybox 无 | package() 手动 shutil.copy2 + chmod 755，附带 man 页与 GPLv3 许可文本 |
| 3 | CI L2 smoke（--version/--help）将失败 | pcapfix 1.1.7 无 -h/--help/--version 选项，无参数才打印 usage 且返回非零 | 已核实 build_and_test.sh L2 为非阻塞 warn（"non-blocking"），test_package 场景 1 显式断言 usage 行为 |
| 4 | Makefile 的 `LDFLAGS += -Wl,-z,relro` | 依赖 `uname` 非 Darwin/CYGWIN（OHOS 上成立） | 不覆盖 LDFLAGS，保留 relro（利于 L4 安全检查） |
| 5 | **真机首编失败：`unknown type name 'u_int32_t'`**（pcap.h 等 10 处，2026-09-18 LAN 机实测） | legacy BSD 类型 u_int8_t..u_int64_t 由 glibc sys/types.h（经 arpa/inet.h 间接引入）提供，musl/OHOS 不提供；上游仅在 `__WIN32__` 分支有 typedef 兜底 | 补丁 0001：pcapfix.h 非 Windows 分支加 `!__GLIBC__/!__APPLE__/!BSD` 守卫的 typedef 块（全部 .c 均先 include pcapfix.h，一处修复全部编译单元；与上游 Windows 侧同款写法） |

## 源码修改

**patches/0001-musl-legacy-uint-types.patch**（portability）：pcapfix.h 非 Windows
分支为 musl 提供 u_int8_t/16/32/64_t typedef（守卫排除 glibc/macOS/BSD，避免重复
定义）。经 `patch -p1` 干跑 + 应用后 diff 验证，与 pipebench 0.40 同款问题的同款解法。

## 依赖版本

无。

## 验证结果

```text
本机（Windows，前置阶段，2026-09-18）：
- sha256 计算与 tar 内容核对 ✅
- conanfile.py / test_package 语法静态检查 ✅（py_compile + yaml 解析）
- 上游修复逻辑源码级走查（pcap.c fix_pcap 全局头分支 + pcapfix.c 退出码）✅
- mock 端到端跑测试脚本 ✅（抓出并修复变量名 bug）

真机（LAN 机 10.62.178.77，2026-09-18 23:51 首验 / 2026-09-19 复验，隔离 CONAN_HOME + download cache 预置）：
- conan create（ohos-aarch64 profile，clang）✅
- test_package 功能测试 9/9 检查点 PASS（"pcapfix smoke test OK"）✅
- 消费者用例 consumer_pcap_repair_pipeline.sh PASS（4/4 记录链、payload 逐字节一致）✅
  —— 模拟下游抓包流水线：358B 夹具（4 包，caplen 60/80/60/70，payload 各异）magic 清零
  → pcapfix 修复 → 下游按 pcap 记录链逐包消费（dd+od 读 u32 LE caplen），断言每包
  caplen、payload cmp、链终点=文件大小
- 产物 bin/pcapfix：59840B，ELF 64-bit arm64 dynamic（musl loader）✅
- 日志留档：设备 $HOME/tmp/pcapfix-job/create5.log
- 首编曾失败：u_int32_t 未知类型（见问题表 #5），补丁 0001 修复后通过
- 消费者夹具首版 ts_sec 误按大端写（相邻包 ts 差 >86400s 触发 pcapfix ASCII 重同步，
  "SUCCESS: 3"+只出 2 包），改统一 LE 现实时间戳后确定性 1 处修复（知识草稿 2 记录）
- 内存安全：全程 free ≈ 740-814MB 平稳，无压力（构建 <1 分钟）
待办：
- shadow CI（CI_PACKAGES 单包）或直接走 finish→submit 流程
```

## 下一步真机/CI 命令

```sh
# 真机（SSH: ssh -T -p 56267 -i ~/.ssh/id_rsa currentUser@frp-tip.com）
# 单包 shadow CI：
CI_PACKAGES="archives/p/pcapfix/1.1.7" zsh ci/conan/build_and_test.sh
# 或 conan create 直验：
conan create archives/p/pcapfix/1.1.7 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 注意事项

- 预计构建耗时 <1 分钟（4 个 .c 文件），远低于默认 3600s 预算，无需 timeout set。
- 本包为 application 类型：软件级 `commands.json` 已按 R38 声明（type=tool，
  commands=["pcapfix"]）。
- 修复 pcapng（`-n`）与 deep scan（`-d`）路径未纳入 test_package（启发式结果
  不完全确定），测试聚焦确定性场景（magic 清零→修复）。
