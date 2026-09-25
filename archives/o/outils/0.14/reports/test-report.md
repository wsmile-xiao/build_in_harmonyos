# outils 0.14 测试报告

## 测试环境
- **平台**: HarmonyOS aarch64（HongMeng Kernel 1.12.0）
- **编译器**: clang 15.0.4（OHOS SDK 26.0.0.18）
- **上游测试**: 无（R51 清点证据见 test_package/MANIFEST.yml）
- **适配回归**: test_package/test.sh（bash，conanrun 环境，实测执行安装后的二进制）

## 测试结果汇总

| 测试 | 通过 | 失败 | 总数 | 结果 |
|------|------|------|------|------|
| 上游测试套件 | 0 | 0 | 0 | 上游无测试（R51 清点） |
| test_package 消费者回归 | 20 | 0 | 20 | ✅ 全部通过 |

## 测试详情（20 条断言）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| md5 stdin / -q | MD5 已知向量 abc | ✅ PASS |
| sha1 / sha256 / sha512 -q | SHA 已知向量 abc | ✅ PASS |
| cksum file | CRC32 + 字节数（1219131554 3） | ✅ PASS |
| md5 file mode | 文件模式输出格式 | ✅ PASS |
| jot 3 | 序列生成 1 2 3 | ✅ PASS |
| lam - | 行拼接管道 | ✅ PASS |
| rs -c | 数组重塑 | ✅ PASS |
| ts | 时间戳前缀 | ✅ PASS |
| vis / unvis | 二进制往返一致性 | ✅ PASS |
| what | @(#) 标记提取 | ✅ PASS |
| apply | 逐参数执行命令 | ✅ PASS |
| lndir | 影子目录软链创建 | ✅ PASS |
| signify | keygen / sign / verify 全链路 | ✅ PASS |
| calendar -f | 直读日历文件 | ✅ PASS |
| calendar #include | 内置展开（鸿蒙特有） | ✅ PASS |
| calendar 随包数据 | calendar.usholiday + CALENDAR_DIR | ✅ PASS |
| rdate | 参数诊断输出 | ✅ PASS |

## 鸿蒙特有测试

1. **calendar 内置 #include 展开**：OHOS 无 /usr/bin/cpp，验证补丁 0005/0006 的展开器（含搜索路径语义）
2. **calendar 随包数据**：`CALENDAR_DIR=<prefix>/share/calendar` 加载 calendar.usholiday
3. **md5 别名**：cksum/sha1/sha256/sha512 以真实副本分发，行为断言与上游一致

## 已知限制

1. `calendar -a`（cron 邮件模式）需要 sendmail，HarmonyOS 无此程序，未测试
2. `rdate` 实际校时需要 root/CAP_SYS_TIME，仅验证参数诊断路径

## 结论

**兼容性评级: 高** —— 全部 17 个命令功能正常，20/20 断言通过；无失败项。
