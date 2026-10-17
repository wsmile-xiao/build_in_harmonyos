# OHOS file(1) 不支持 -Pbytes/-i：TAP 辅助脚本 mimetype 探测移植方案

- 草稿 ID: DRAFT-OHOS-FILE1-MIMETYPE-PORTABILITY
- 来源: jenkins-debian-glue 0.23.6 适配（tap/jdg-tap-shellcheck 等脚本）
- 类别: portability / ohos-platform / testing

## 现象

`file -Pbytes=32 -b -i <file>` 在鸿蒙 PC 上报
`file: Unknown option 'Pbytes=32'`（去掉 -Pbytes 后 `-i` 也报
`Unknown option 'i'`），mimetype 探测结果为空。依赖该探测的
TAP 辅助脚本（jdg-tap-shellcheck / jdg-tap-checkbashism /
jdg-tap-pep8 / jdg-tap-perlcritic）对所有输入输出
`doesn't look like sh code []. Ignoring.` 并跳过检测，上游测试
`tests/file-detection` 期望的 `1..0` 断言失败。

## 根因

鸿蒙 PC 的 file(1) 为精简实现，无 GNU file 的预读控制（-Pbytes）
与 --mime（-i）选项。

## 修复（两平台行为等价）

```diff
-mimetype = `file -Pbytes=32 -b -i #{file}`.gsub(/\n/,"")
-if not /.*x-shellscript/i.match(mimetype)
+mimetype = `file -b #{file}`.gsub(/\n/,"")
+if not /script/i.match(mimetype)
```

- `file -b`：GNU 与 OHOS 均支持；
- 正则放宽为 `/script/i`：Debian 输出 "POSIX shell script text
  executable" 命中，OHOS 输出 "/bin/sh script" 命中，检测语义不变；
- **命令与正则必须成对修改**：jdg-tap-pep8 曾出现单边修改（探测命令
  `-b -i`→`-b` 但保留 `x-python` mimetype 正则）——`file -b` 输出
  "python3 script" 不含 `x-python`，门控恒真，所有 Python 文件被静默
  跳过（漏检）。pep8 的正确改法为 `/.*x-python/i ...` → `/python/i`；
  改造任何此类脚本时必须同步核对探测命令与正则两半；
- 对断言完整文案（含 mimetype 原文）的测试，放宽为稳定前缀/后缀
  断言——方括号内容是平台 file 实现输出，不可跨平台字节级断言。

## 验证

补丁后 jenkins-debian-glue test_package 实测 21/21 通过：
jdg-tap-shellcheck 对 shell fixture 输出 `1..0`（与上游期望一致）、
jdg-tap-perlcritic 输出 `File ... doesn't look like perl [/bin/sh
script]. Ignoring.`（检测行为等价）；pep8 tap 以 fake pycodestyle
shim（仿上游 tests/file-detection 惯例）验证：Python fixture 通过门控
交给工具（旧行为为静默跳过，可被该用例拦截）、shell fixture 仍被
正确忽略。

## 适用面

任何用 file(1) 做 mimetype 探测的脚本工具（TAP 辅助、lint 包装器、
文件类型分发器）在 OHOS 上的适配。
