# lzd 1.5 知识证据报告

- 真机：10.195.180.238，隔离 job `device-b/lzd-kb-20260920`；2026-09-20
- 环境：clang 15.0.4（aarch64-unknown-ohos）、Conan 2.29.1

## EVID 矩阵（全部 target-executed）

| EVID | 结果 |
|---|---|
| EVID-01 | conan create 退出码 0（自研 configure + Makefile.in，无补丁） |
| EVID-02 | build() 内 `make check` 上游套件执行（check.sh 以 stdin/stdout 调用 lzd，fox*.lz 10 变体 + em.lz） |
| EVID-03 | 消费者 3/3：fox-decode: OK / em-decode: OK（空成员语义）/ negative-control: OK（垃圾输入被拒） |

## 适配要点

- 自研 configure（Antonio Diaz Diaz 系，非 autoconf）：直接 `./configure CXX=<conf> CXXFLAGS=-O2 --prefix=<pkg>` 即可，无需 autoreconf
- 上游 tarball 不含 doc/lzd.1（man 需 makeinfo 生成）：`make install-man` 必败 → 只 install-bin
- **lzd 无任何命令行选项**（连 -d/-c 都没有）：仅 stdin→stdout，与上游 check.sh 的调用方式一致（`"${LZIP}" < in > out`）
- **em.lz = 空成员**（解压输出为空文件，check.sh:58-60 语义）：消费者断言须 `[ ! -s ]` 而非 `[ -s ]`

## 测试统计

上游 make check（fox 10 变体 + em + 坏输入等约 20+ 断言）；消费者 3/3。

## 影子 CI
【待回填】
