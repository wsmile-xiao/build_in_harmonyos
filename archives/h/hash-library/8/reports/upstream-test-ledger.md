# hash-library 8 上游测试台账（源码声明口径）

## 源码声明枚举（官方 tag hash_library_v8 = 70cc93763d49a24c4536c7f0a23248f9b40e30f5）
- 官方源码 tests/ 目录 3 个独立测试可执行（各含 int main 用户用例）：
  1. tests/tests.cpp — 主套件（100 组自动向量 + SHA1/SHA2-256/SHA3-256/512/224/Keccak-224 + HMAC(MD5,SHA1,SHA256) RFC2202/4231）→ 独立用户用例 1
  2. tests/github-issue2.cpp — issue#2 回归（重复 getHash 幂等）→ 独立用户用例 1
  3. tests/github-issue6.cpp — issue#6 回归（SHA3-512 大向量）→ 独立用户用例 1
- 框架/样例/基准排除：digest.cpp 是 CLI 示例工具（非测试）；根目录无其它测试声明。

## 双口径统计
- source_declared_total = 3
- configured_executable_total = 3（无互斥编译分支，全实例化）
- executed_passed_total = 3
- 未运行/未实例化 = 0
- 全量通过率 = 3/3 = 100%

## 逐项映射（声明 -> 构建目标 -> 执行 -> 结果）
1. tests/tests.cpp -> clang++ tests.cpp crc32 md5 sha1 sha256 sha3 keccak -o tests-run -> ./tests-run -> rc=0 "all tests ok"
2. tests/github-issue2.cpp -> clang++ github-issue2.cpp sha1 sha256 sha3 keccak md5 -o issue2 -> ./issue2 -> rc=0
3. tests/github-issue6.cpp -> clang++ github-issue6.cpp sha3 -o issue6 -> ./issue6 -> rc=0

## 执行环境
- clang 15.0.4 (OHOS toolchain /data/service/hnp/bin/clang++)
- OHOS aarch64，c++17，-fPIC -O2
- 2026-09-22
