# 官方测试说明

gdbm 1.23 项目未提供 `make check` 或类似的自动化测试套件。

因此，本次测试使用自定义测试程序验证库的核心功能。

## 替代测试方案

- 链接测试脚本: `../custom/test-scripts/test-link.sh`
- API 测试程序: `../custom/test-scripts/test-gdbm-api.c`
- 测试结果: `../custom/results/test-link.log`