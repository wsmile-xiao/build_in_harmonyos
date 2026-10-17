# swish-e 2.4.7 适配笔记

## 上游测试实测记录（R51 三步法，2026-10-02）

- **清点**：tarball `tests/` 共 16 文件；套件实为 4 个 check 脚本
  （check_index / check_search / check_metasearch / check_fuzzy），
  经 `tests/Makefile.am` 的 `TESTS` 挂在 `make check` 下，驱动 CLI 对
  fixture（test.html/test.xml/test_meta*.html 等）建索引+检索。
- **运行环境**：本机 OHOS 设备原生 shell，perl 5.42（aarch64），
  已构建树 `~/tmp/swish-debtest/swish-e-2.4.7`（src/swish-e 可执行）。
- **实测命令**：`cd tests && make check`
- **结果**：4/4 PASS ——
  `PASS: check_index / check_search / check_metasearch / check_fuzzy`
  `All 4 tests passed`（rc=0）。覆盖全部 16 个测试资产。
- 结论：此前 PR 描述"依赖 perl+安装树不可离线执行"不准确——
  perl 在目标环境可用、已构建树即可运行，已真实执行并全数通过。

## 已知限制

- 2009 代码在 64 位 `-O2` 下 worddata 写入路径优化期 SIGSEGV
  （`remove_worddata_longs`，指针/long 双关疑似），配方钉 `CFLAGS=-O1`。
- config.guess timestamp 2009-04-27 无 aarch64 分支，需显式
  `--build=aarch64-unknown-linux-gnu`（知识库 CONFIG-GUESS-BUILD-TYPE-OHOS）。
