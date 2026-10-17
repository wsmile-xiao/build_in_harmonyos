# pnglite 0.1.17 上游测试清点台账

## 来源

- 官方发布页：https://sourceforge.net/projects/pnglite/files/pnglite/0.1.17/
- 官方归档：`pnglite-0.1.17.zip`
- SHA-256：`6444b13b9ec5b6f9de8f72513a00870325779e3b05bfcf554edb1ab0c90f5962`

## 三步清点结果

1. 文件清点：归档仅含 `pnglite.c` 和 `pnglite.h`，普通文件数为 2。
2. 测试注册清点：无 `tests/`、`test/`、CTest、Make、Meson、Autotools 或其他测试入口，注册测试数为 0。
3. 可执行性核验：无测试程序、示例程序或测试命令可执行，上游实测为 0/0。

清点命令：

```bash
unzip -Z1 pnglite-0.1.17.zip
find . -maxdepth 3 -type d -iname '*test*'
rg -n -i 'test|check|ctest|assert|main\s*\(' .
```

## 适配后补全

| 测试 | 类型 | 断言数 | 结果 |
|------|------|--------|------|
| `test_pnglite.c` | 公共 API 消费者测试 | 20 | PASS |
| `harmonyos_specific_test.c` | HarmonyOS AArch64/musl 专项测试 | 5 | PASS |
| **合计** | | **25** | **2/2 PASS** |

适配后的测试数为 2，不少于上游实测的 0；其中包含 1 个 HarmonyOS 特有测试。
