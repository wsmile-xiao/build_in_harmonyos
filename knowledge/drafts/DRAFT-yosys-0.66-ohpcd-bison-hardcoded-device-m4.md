# DRAFT-yosys-0.66 — 制品仓 bison 硬编码设备 m4 路径

## 使用说明

在非鸿蒙主机（WSL / x86 交叉环境）上用制品仓的 `bison/3.8.2` 生成语法分析器时，
bison 会去调 `/data/service/hnp/bin/m4`（**编译进二进制的设备路径**）。该路径不存在时，
make 常常只报 `Error 141`（SIGPIPE 派生），真实报错被吞掉。

三步定位：

```bash
# 1) 实证硬编码路径
strings <bison 包>/bin/bison | grep -F '/data/service/hnp'
#   -> /data/service/hnp/bin/m4

# 2) 看真实报错（不要只看 Error 141）
grep -n 'input/output error' <build log>

# 3) 排除磁盘/权限（对照实验）
#   普通 OHOS aarch64 二进制在同主机读写文件正常 -> 与磁盘无关
```

处置：只在设备路径**不存在**时注入 `M4=`：

```python
parts = []
if not os.path.exists("/data/service/hnp/bin/m4"):
    which_m4 = shutil.which("m4")
    if which_m4:
        parts.append('M4="%s"' % which_m4)
```

这样鸿蒙设备/实机 CI 上分支不触发，行为与官方一致。

## 适用范围

- 工具：conan 制品仓的 `bison/3.8.2`（OHOS aarch64 二进制）
- 阶段：compilation（bison 生成 parser）
- 主机：非鸿蒙主机（该设备路径不存在）；鸿蒙设备不受影响
- 不适用：用系统自带 bison 的构建

## 输入输出定义

- 输入：`os.path.exists("/data/service/hnp/bin/m4")` 探测结果 + `shutil.which("m4")`
- 输出：make 环境前缀中的 `M4=<abs>`（与 `BISON_PKGDATADIR=<bison 包>/share/bison` 一起）
- 成功信号：`frontends/verilog/verilog_parser.tab.cc` 生成完成，make 继续

## 示例

```
$ make -j1 ...
[ 16%] Building frontends/verilog/verilog_parser.tab.cc
make: *** [frontends/verilog/Makefile.inc:9: frontends/verilog/verilog_parser.tab.cc] Error 141

$ grep -n 'input/output error' build.log
bison: input/output error                     # 真实错误

$ strings .../bison/p/bin/bison | grep -F '/data/service/hnp'
/data/service/hnp/bin/m4                      # 根因

# 加 M4= 后：
$ M4=/usr/bin/m4 BISON_PKGDATADIR=.../bison/p/share/bison make -j1 ...
[ 16%] Building frontends/verilog/verilog_parser.tab.cc    # 通过，RC=0
```

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `DRAFT-autotools-ac-prog-lex-demotes-lex-when-libfl-unlinkable` | 都与 bison/flex 工具链有关 | 那条是 configure 探测把 lex 降级；本条是**制品仓工具包二进制硬编码设备路径**，需要条件注入 `M4=` |
| `cvs-fast-export-1.59-generated-parser-sources-vs-regen-rules` | 都关于 parser 生成 | 那条是时间戳触发再生成；本条是 m4 路径缺失 |
| **E335**（`draft-review` 预审建议 `review-similar → E335`） | 关键词层面都出现 m4/工具链相关词 | **实为误匹配**：E335 讲的是 `gitlab.alpinelinux.org` 返回 HTTP 418 导致 ACF 模块源码无法下载（网络反爬），与本条的「制品仓 bison 二进制硬编码设备路径 `/data/service/hnp/bin/m4`」无共同根因、无共同处置。建议仍按 `create` 处理 |

## 验证证据

```
$ strings /home/qianxia/.conan2/p/bison.../p/bin/bison | grep -F '/data/service/hnp'
/data/service/hnp/bin/m4

$ ls /data/service/hnp/bin/m4
ls: cannot access '/data/service/hnp/bin/m4': No such file or directory   # RC=2

# 对照实验：普通 OHOS aarch64 二进制文件 I/O 正常
$ /tmp/_probe_arm            # 读文件 -> READ_OK
$ /tmp/_probe_arm            # 写文件 -> WRITE_OK

# 注入 M4= 后 yosys 构建完整通过
$ conan create archives/y/yosys/0.66 ...
yosys/0.66: Package 'c42828e97568cfa87dd952edd6ec0ca8338078f6' created   # EXIT=0
```

- 退出码：修复前 make=2（Error 141）；修复后 conan create=0
- 日志绝对路径：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/033-local-create.log`
- 上游任务：PR #11115
