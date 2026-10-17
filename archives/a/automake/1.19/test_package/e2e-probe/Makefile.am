## 下游微型 autotools 工程（消费者端到端用例 fixture）
## 由被测的 automake 1.19 生成 Makefile.in，随后走 configure → make →
## make check → make install 全链路。
##
## 并行测试 harness（automake 1.13+ 默认）真机适配要点：
## LOG_COMPILER=sh 让每个测试脚本经 sh 执行（OHOS 内核拒绝 shebang
## execve）。不能用 TESTS_ENVIRONMENT=sh——它在 parallel harness 里被
## 拼在 LOG_DRIVER 之前（am__check_pre 尾部），会展开成
## "sh /bin/sh ./test-driver"，即拿 sh 把二进制 /bin/sh 当脚本执行
## （syntax error: unexpected ELF 字节）。
bin_SCRIPTS = probe
TESTS = probe
LOG_COMPILER = sh
EXTRA_DIST = configure
