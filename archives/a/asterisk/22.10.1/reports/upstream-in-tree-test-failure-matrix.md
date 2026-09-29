# 上游 in-tree 用例失败矩阵（asterisk 22.10.1 / 真机实测）

执行提交 `a6d20a0ac9`，实测 572 条用例，其中 12 条 FAIL。逐条给出证据 XML、
原始错误行与根因分类。

分类口径：

- **运行夹具**：失败源于测试运行环境（可写临时目录、配置、声音资源），不是制品缺陷；
  修复方式是补齐 runner 夹具，不需要改配方。
- **平台工具链契约**：失败源于设备 shell/工具行为与上游假设不一致，需要独立测试适配。
- **平台语义差异**：失败源于内核/库语义差异（poll readiness），需要独立内核行为适配评估。

## 失败清单

| # | 用例 | 证据 XML | 关键错误行 | 分类 |
|---:|---|---|---|---|
| 1 | `/funcs/func_env/func_file` | `_funcs_func_env_.xml` | `test_func_file.c:289: Cannot open test file: No such file or directory` | 运行夹具（`/tmp` 只读） |
| 2 | `/funcs/func_sayfiles/test_SAYFILES_function` | `_funcs_func_sayfiles_.xml` | `func_sayfiles.c:193: SAYFILES(hi Th3re,alpha) test failed ('')` | 运行夹具（声音资源与语言数据） |
| 3 | `/main/file/read_dir_test` | `_main_file_.xml` | `test_file.c:72: Failed to create directory: /tmp/tmpdir.XXXXXX/XXXXXX` | 运行夹具（`/tmp` 只读） |
| 4 | `/main/json/dump_load_file` | `_main_json_.xml` | `test_json.c:1301: Condition failed: NULL != file` | 运行夹具（`/tmp` 只读，用例使用 `/tmp/ast_json.XXXXXX`） |
| 5 | `/main/media_cache/create_update_metadata` | `_main_media_cache_.xml` | `test_media_cache.c:364: Condition failed: res == 0` | 运行夹具（`/tmp` 只读） |
| 6 | `/main/media_cache/create_update_nominal` | `_main_media_cache_.xml` | `test_media_cache.c:236/238: Creating resource with /tmp/test-media-cache-XXXXXX; Condition failed: res == 0` | 运行夹具（`/tmp` 只读） |
| 7 | `/main/poll/poll_test` | `_main_poll_.xml` | `test_poll.c:95/101: Creating handle that should NEVER block on write/read` 后断言失败 | 平台语义差异（poll readiness） |
| 8 | `/main/stdtime/timezone_watch` | `_main_stdtime_.xml` | `test_time.c:90: Querying timezone /tmp/timezone.XXXXXX/test` 后失败 | 运行夹具（`/tmp` 只读 + 时区数据目录） |
| 9 | `/main/test_capture/test_capture_stdout_stderr` | `_main_test_capture_.xml` | `test_capture.c:331: unexpected value for stdout` | 平台工具链契约（设备 `sh`/coreutils 输出） |
| 10 | `/main/test_capture/test_capture_with_dynamic` | `_main_test_capture_.xml` | `test_capture.c:272: unexpected value for stdout`（`date --date=@<epoch>`） | 平台工具链契约 |
| 11 | `/main/test_capture/test_capture_with_stdin` | `_main_test_capture_.xml` | `test_capture.c:196: unexpected value for stdout`（`base64` 管道） | 平台工具链契约 |
| 12 | `/main/voicemail_api/nominal_msg_playback` | `_main_voicemail_api_.xml` | `test_voicemail_api.c:1431: Created message ... /Old with ID ...` 之后播放断言失败 | 运行夹具（voicemail 配置与声音文件） |

## 汇总

| 分类 | 数量 | 可否在本 PR 内修复 |
|---|---:|---|
| 运行夹具（`/tmp` 只读、声音与配置缺失） | 8 | 否（属测试 runner 夹具，按"一库一 PR"边界不在本 PR 的配方范围内） |
| 平台工具链契约（capture 的 stdout 契约） | 3 | 否（需独立测试适配评估） |
| 平台语义差异（poll readiness） | 1 | 否（需独立内核行为评估） |

补充说明：运行夹具类里 `/tmp` 相关的 6 条，直接在设备上把 `/tmp` 前缀重定向到可写目录
（LD_PRELOAD 夹具）仍不能全部通过，因为部分用例（如 `test_file.c`）用 `mkdtemp()` 就地改写模板
字符串后再拼子目录，重定向层无法把改写后的路径回写进调用方缓冲区。这类用例需要按测试适配 PR
逐个改造，不属于制品交付范围。

## 复现方式

```bash
# 单条用例复现（示例：poll）
"$PKG/sbin/asterisk" -fgn -C "$PKG/etc/asterisk/asterisk.conf" &
"$PKG/sbin/asterisk" -rx 'test execute category /main/poll/' -C "$PKG/etc/asterisk/asterisk.conf"
"$PKG/sbin/asterisk" -rx 'test generate results xml /tmp/poll.xml' -C "$PKG/etc/asterisk/asterisk.conf"
cat /tmp/poll.xml
```

设备上的原始控制台与命令日志：`.../testfw/categories/<类别>-console.log`、`<类别>-command.log`。
