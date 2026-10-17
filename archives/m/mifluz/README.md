# mifluz 0.26.0 — HarmonyOS PC 适配

GNU mifluz 是 C++ 全文倒排索引库（ht://Dig 血统），内嵌 htdb/db 存储层，
提供词索引、布尔查询与缓存管理能力。

## 本归档

- 上游：https://ftp.gnu.org/gnu/mifluz/mifluz-0.26.0.tar.gz
- 适配版本：0.26.0（首次适配）
- 构建系统：autotools
- 产物：`libmifluz.a/.so`（单一大库，内嵌 db/htdb/clib）
- Conan 引用：`mifluz/0.26.0`（`cpp_info.libs = ["mifluz"]`）

## 适配要点

1. 交叉编译 AC_TRY_RUN 的 8 个 db_cv_* 缓存变量以 aarch64 事实值预设
2. config.guess/sub 升级 + ohos triplet
3. configure 的 umask 077→022（E011）+ ac_pwd/ls -di 的 HMDFS getcwd 回退
4. clang 15 硬错误修复：WordTree.cc switch 收窄、example1.cc 字符字面量转义
5. 消费者测试 test_mifluz：WordContext/WordList 建库-插入-检索全链路断言

## 版本

- 0.26.0：首次适配（详见 0.26.0/notes.md）
