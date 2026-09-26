# mustang 3.2.4 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，由 profile 的 tools.build:compiler_executables 注入）
- 状态: built

## 编译步骤
1. W0 preflight：零外部依赖（Debian Build-Depends 仅 debhelper），直接通过。
2. 源码核验：自行重新下载实算 sha256 = c05e91c955f491a1fddc404a36ef963b057fd725bcc6d22ef6df1c23b26ce237。上游官方站点（lcb.infotech.monash.edu.au/mustang）的 mustang_v3.2.4.tgz 实算 sha256 与 Debian orig 逐字节一致（同一原封产物）。官方站 TLS 链配置有误（叶证书由 Sectigo R36 签发、服务端却下发旧代 Sectigo RSA OV 中间证书，python 报 unable to get local issuer certificate，标准 CA 包亦无法补齐缺失的中间证书），故 conandata 采用 URL 列表：官方站点优先、Debian 源码存档回退（两 URL 同一文件）；此为 PF7 已知例外口径，PR 正文需说明并由提审方决定是否启用 --no-preflight。
3. 手工探索编译：`make -j1 CPP=<clang++> CPPFLAGS="-Wall -O3"` 一次通过（仅 2 个无害 -Wheader-guard 告警）。
4. conan 配方：build() 在 make 命令行覆盖 CPP/CPPFLAGS（R33：编译器取 profile conf，不依赖 shell 环境变量）。
5. package()：上游无 install 目标，自行搬运 `bin/mustang-3.2.4` 并改名为 `bin/mustang`，man 页装到 `share/man/man1/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 CPP=g++（设备无 g++/c++） | 上游按 Linux/GCC 写死 | make 变量覆盖 `CPP=<clang++>`（无补丁） |
| 2 | CPPFLAGS 含 `-traditional`，clang 报 unknown argument | 该旗标仅 GCC cpp 认识 | make 变量覆盖 `CPPFLAGS="-Wall -O3"`（无补丁） |
| 3 | README 冒烟首次 RC=1：`Error Opening File:./data/test/pdbs/*` | 描述文件内 PATH 为相对路径，必须在源码根目录执行（执行者操作失误，非上游缺陷） | cd 到源码根目录重跑，RC=0，产出 results.html + results.pdb |

## 源码修改
无补丁、无源码修改（全部通过 make 命令行变量覆盖解决）。

## 依赖版本
无依赖。

## 上游测试清点（R51 三步法）
1. **清点**：Makefile 目标仅 `all`/`clean`/`remove`，无 check/test 目标；源码树无 tests/ 目录；无 ctest/pytest 注册 ⇒ **上游自动化测试 0 个**（TESTS=False 申报成立）。
2. **运行**：上游 README 记载的唯一验证手段（手工冒烟）已在本机执行：`./bin/mustang-3.2.4 -f ./data/test/test_zf-CCHH`（15 个 zf-CCHH 锌指 PDB）→ RC=0，产出 results.html（24926B）与 results.pdb（244459B），与 README 预期一致。另以 2 个 PDB（1znf/1znm）做了 `-F fasta` 比对抽测，out.afasta 序列比对结果合理。
3. **回填**：`upstream_tests: []`（自动化）；README 手工冒烟已执行通过（N=1，证据见本 notes 与 reports/）；test_package 另带消费者冒烟：合成 20 残基聚丙氨酸螺旋×2 真实比对，断言退出码与 FASTA 输出特征。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh mustang/3.2.4   # OK（零依赖）
make -j1 CPP=clang++ CPPFLAGS="-Wall -O3"          # RC=0，bin/mustang-3.2.4 (231936B)
./bin/mustang-3.2.4 -f ./data/test/test_zf-CCHH    # RC=0，results.html+results.pdb
python3 scripts/ohc-run.py conan-verify mustang 3.2.4   # 结果见 reports/
```

## 零特殊机制声明
本次适配未撞出任何新机制：编译器替换走 make 变量覆盖（通用已知打法），无平台宏、无补丁、无依赖。B 判定预期 none。

### 对话 #1（2026-09-25 适配会话，z31-mustang）

- W0 依赖：零外部依赖（Debian Build-Depends 仅 debhelper），preflight 直接通过；sha256 自行重新下载实测，与 init-build 记录一致。
- W1 配方：裸 Makefile，make 命令行变量覆盖 CPP=<clang++>、CPPFLAGS="-Wall -O3"（去 -traditional）；无补丁、无平台宏。
- W2 构建：探索编译一次通过（仅 2 个无害 header-guard 告警）；conan create（G2 干净构建）通过。
- W3 测试：上游无自动化测试（R51 清点，Makefile 无 check 目标）；README 手工冒烟实机执行通过（results.html+results.pdb）；test_package 合成 PDB 消费者冒烟 4 断言全 PASS；conan-verify 8 闸 PASS；W3 本地 CI 模拟通过。
- 收尾：verify-build PASS → PackageBuilder 产出 packaging/release 249KB + debug 65KB；.staging-verified 与 .knowledge-done 标记落位。
---

**编译结束**: 2026-09-25 02:53
**最终状态**: built
