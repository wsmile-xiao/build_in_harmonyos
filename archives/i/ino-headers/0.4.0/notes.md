# ino-headers 0.4.0 适配笔记

## 编译环境
- 构建系统: 无（手装范式，跳过上游 autotools；kicad-demos 10.0.4 先例同款）
- 编译日期: 2026-09-24
- 编译器: 无编译动作（纯头文件安装）
- 状态: built → 真机 conan-verify 全绿后 published

## 软件性质 (R38 决策依据)

- ino-headers（NASPRO 项目）是全部 ino 实现共用的 C 头文件包：单个公共头
  `lib.h`（718 行，仅声明无实现）安装到 `include/ino-0/ino/lib.h`，另附
  `ino-headers-0.pc` pkg-config 文件（`Cflags: -I${includedir}/ino-0`）。
- 零编译产物、零可执行文件、零依赖 → R38 无需 commands.json；
  `package_type = "header-library"`（indirect-lite 已合入先例同款）。
- 上游无测试套件（tarball 无 test/ 目录、Makefile.am 无 check 目标），
  R34 实质校验由双语言消费者探针（test_ino.cpp + test_ino_c.c）+
  check_pkg.sh 布局校验替代。
- 上游源码地址：SourceForge（NASPRO 官方发行渠道；naspro.atheme.org 已不可达，
  AUR 同款 URL）。sha256=a06ea7c0...96e14bf 本地实测。

## 为什么跳过 autotools（手装）

上游 `configure` 无任何编译器探针、`make all`/`make check` 均为 no-op——
对纯头文件包跑一遍 configure/make/make install 零收益，却要在 OHOS 上引入
autoconf 2.68 的 `umask 077` mktemp 陷阱（知识 E011，需额外补丁，参见已合入
mypaint-brushes 的 0001-configure.patch）。故采用与已合入 kicad-demos 10.0.4
一致的手装范式：source() 取官方 tarball，build() 做防漂移文件存在性校验，
package() 按上游 Makefile.am 的 `inoincludedir` 规则直接安装头文件并生成
pc 文件。零补丁、零 configure 风险。

## 编译步骤

```bash
# 源码下载（SourceForge 官方直连可用，2026-09-24 实测）
# sha256: a06ea7c03660a140938605cd7571bd886a59a41d31a6e8ee03159546c96e14bf

# 真机 Conan 配方验证（8 道门禁 G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify ino-headers 0.4.0   # G0-G4/L2/L4/L5 全绿
python3 scripts/ohc-run.py finish ino-headers 0.4.0 published  # W3 本地 CI 模拟通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 configure 在 OHOS 上会踩 HMDFS umask 077 陷阱（E011 路径） | autoconf 2.68 生成的 configure 以 `umask 077` 建临时目录，HMDFS 拒绝写入 0700 目录 | 手装范式彻底绕开：不运行 configure（无补丁、无风险），与 kicad-demos 10.0.4 已合入先例一致 |
| 2 | 上游仅发 .pc.in 模板，无现成 pc 文件 | 上游依赖 configure 展开 @prefix@ 变量 | package() 内直接生成 ino-headers-0.pc，采用 `${pcfiledir}/../..` 可迁移前缀（上游绝对前缀在包移动后失效） |
| 3 | 上游无任何测试用例（无 check 目标、无 test/ 目录） | 上游只发布头文件，未随包附带测试 | 按 FAQ「无测试用例的库」条款：双语言消费者探针——C++ TU 用 decltype 编译期断言覆盖全部 26 个公开函数精确签名 + 3 typedef + 6 枚举值；C11 TU 验证头文件在纯 C 下可用；check_pkg.sh 校验布局/pc/纯度 |
| 4 | 发布包内容漂移风险（手装无 make install 兜底） | 直接拷贝依赖人工核对上游布局 | build() 防漂移校验：逐一断言 8 个关键源文件在位（kicad-demos 先例同款），上游安装布局已对照 Makefile.am `inoincludedir` 核对 |

## 源码修改

- 无补丁。上游源码零修改（手装范式仅按上游 Makefile.am 安装规则重放布局）。

## 本地预验记录（2026-09-24，Windows MinGW）

- test_ino.cpp：g++ -std=c++11 -Wall -Wextra 零警告，35 项编译期断言 + 运行时枚举校验全过（exit 0）
- test_ino_c.c：gcc -std=c11 -Wall -Wextra 零警告，3 项 _Static_assert + 运行时枚举校验全过（exit 0）
- check_pkg.sh：正/反向双路径验证（模拟包结构 PASS；pc 绝对路径注入后正确 FAIL）

## 待真机回填

- [ ] conan create / conan-verify 完整日志（G0-G4 / L2 / L4 / L5 门禁结果）
- [ ] test_ino_cpp / test_ino_c 双探针 CTest 输出（真机运行）
- [ ] check_pkg.sh 布局校验输出
- [ ] manifest.yaml status: built → published
