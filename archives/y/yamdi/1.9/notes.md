# yamdi 1.9 适配笔记

## 任务来源

- 平台任务 contrib-12252（开源鸿蒙PC专项积分赛），分支 `feat/yamdi-1.9`，2026-09-19 认领
- 上游：https://github.com/ioppermann/yamdi （54 stars，非 fork，tag 1.9 实拉核验存在）
- 语言实测（R47 lang-preflight）：C（单源文件 yamdi.c 2388 行，占比 100%）

## 选库核验（§3.2 否决线）

1. 他人已移植：`archives/` 全量比对 + `git grep yamdi` 同源反查均无；制品仓无 yamdi 任何版本
2. 语言/构建生态：C + 直接编译，CI 工具链具备
3. 难度定级：A（纯编译适配）——零外部依赖

## 上游测试清点（R51）

- 上游**无测试套件**：全仓 7 个条目（CHANGES/LICENSE/Makefile/Makefile.mingw32/man1/README/yamdi.c），无 tests/、无测试目标
- 因此申报：上游测试 0 项；验证由 test_package CLI 功能测试承担（7 项断言）

## 平台适配要点

- **上游 Makefile 不可用**：硬编码 gcc、install 规则要求 root + /usr/local——配方直接编译单文件
- **musl getopt 不认长选项**：`--version`/`--help` 返回 '?' 退出 1，`-h` 也退出 1（YAMDI_ERROR）——L2 smoke test 需要帮助/版本探针退出 0，补丁 0001 在 getopt 前拦截两个长选项并以 0 退出
- **LD_LIBRARY_PATH 盾**：build() 显式清空（lld/libxml2 根因，同 libodfgen/libabw）

## 编译结束

设备实机验证（2026-09-19，OHOS aarch64）：

- `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（RC=0）；test_package 8 项断言全过
- CI 同源闸门 `CI_PACKAGES=archives/y/yamdi/1.9 zsh ci/conan/build_and_test.sh`：L0/L1/L4/L5 全 pass，Pass rate 100%，RC=0
- 产物：bin/yamdi（静态单文件工具，零依赖）

踩坑记录（已修复）：

1. 上游 Makefile 硬编码 gcc 且 install 要 root → 配方直接编译
2. musl getopt 不认 --version/--help 且 -h 退出 1 → 补丁 0001 拦截长选项以 0 退出（L2 smoke test 要求）
3. conan test 环境下对二进制产物 grep 长字符串不稳定 → 元数据断言改用 yamdi 自带的 XML 导出（-x，纯文本）
