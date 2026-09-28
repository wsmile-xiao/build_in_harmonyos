# Test Report — zlog 1.2.18 (R02)

**软件**: zlog 1.2.18 | **平台**: OHOS aarch64 (ohos-aarch64 profile, clang-15) | **日期**: 2026-09-21
**运行环境**: 本机 aarch64 OHOS PC（官方补丁源码经 `clang --target=aarch64-linux-ohos` 构建后原生执行）

## 1. Conan L1 test_package（`conan create` 内嵌执行）

- 命令: `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
- 结果: **PASS**（exit 0）；`test_zlog` 编译并运行，输出 `test_zlog:OK`
- 执行证据: `reports/conan-create-r02.log`（SHA-256: `5067142f0c1998f11e9fc01dd7cfa9c10a237d6031935b9e05785470c2760b9e`）
- 覆盖: `zlog_init_from_string` / `zlog_get_category` / `zlog_info` / `zlog_level_enabled` / `dzlog_init` / `dzlog_info` / `zlog_fini`

## 2. 上游测试（R51 三步法，官方归档 `test/` 目录 27 个 `test_*.c` 入口）

- 清点: 27 个 `test_*.c`；`makefile` `exe` 列表注册全部 27 个；`CMakeLists.txt` `aux_source_directory` 自动注册 + `not_auto_add_test` 排除 11 个 + `add_test` 补回 3 个
- 编译: 27/27 全部经 `clang --target=aarch64-linux-ohos` 编译通过
- 实测统计: **通过 25 / 失败 1 / 受控观察 1 / 未运行 0**
  - pass: test_buf, test_category, test_conf, test_default, test_enabled, test_hashtable, test_hello,
    test_init, test_level, test_mdc, test_pipe, test_profile, test_prompt, test_record, test_syslog, test_tmp,
    test_bitmap(0xaa55 0x66), test_hex(test_hex.conf 3), test_leak(5), test_longlog(2222),
    test_press_write(1 1 3), test_press_write2(1 1 3), test_press_zlog(1 1 3), test_press_zlog2(1 1 3), test_press_syslog(1 3)
  - fail: test_conf2（`zlog_init` exit 255；经 `zlog-chk-conf` 实证为上游内嵌配置 `[formats] null = "%n"` 解析失败，非本库适配缺陷）
  - 受控观察: test_multithread（`while(1)` 多线程持续运行，无官方终止参数，`timeout 25s` 观察运行正常后超时结束，不计入通过/失败）
- 申报表: 见 `notes.md`「上游测试申报表」

## 3. 鸿蒙特有测试（适配交付硬门禁）

- 测试文件: `test_zlog_ohos.c`（外置运行，非 test_package 内容），验证 OHOS 平台适配路径：
  1. OHOS `/tmp` 只读环境下配置文件输出重定向到 CWD 可写路径（`"ohos-test.log"` 引号语法）
  2. 级别过滤真实行为（`ohos_cat.INFO` 规则丢弃 DEBUG 记录）
  3. 日志文件内容回读断言（磁盘真实写盘，非 stdout 回显）
  4. `dzlog_init`（配置文件路径形式）默认分类流程
- 结果: **PASS**（exit 0，输出 `test_zlog_ohos:OK`）；日志文件仅含 `INFO ohos-write-1`、无 DEBUG 泄漏
- 运行命令: `clang -O2 -Wall -D_GNU_SOURCE --target=aarch64-linux-ohos -I<src> -o test_zlog_ohos ... -L<lib> -lzlog -lpthread && LD_LIBRARY_PATH=<lib> ./test_zlog_ohos`
- 执行证据: `reports/harmonyos-specific-test.log`（SHA-256 见回报 evidence）

## 4. 汇总

| 项目 | 结果 | 通过/总数 |
|------|------|-----------|
| Conan L1 test_package | PASS | 1/1 |
| 上游测试（实际运行） | PASS | 24/25（1 上游配置缺陷 + 1 受控观察） |
| 鸿蒙特有测试 | PASS | 1/1 |