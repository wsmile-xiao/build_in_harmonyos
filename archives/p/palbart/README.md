# palbart

[GNU barcode](https://www.gnu.org/software/barcode/) 2.14 的 **PostScript 后端驱动** ——
条码描述语言的解释器与编码器。

## 它做什么

给定一份纯文本的条码描述文件（符号表 + 字模定义），`palbart` 边解释边输出两份产物：

| 产物 | 内容 |
|---|---|
| `<输入名>.lst` | 可打印的符号清单：逐行回显输入、给出每行在 `.bin` 中的字节偏移，末尾汇总诊断与链接生成情况 |
| `<输入名>.bin` | 编码后的条码位流（记录头 + 各符号的位段） |

> 它**不是**排版器。真正的 PostScript 渲染由下游的 gnuplot / ghostscript 等完成，
> 本包刻意不安装这些工具——渲染后端由调用方决定。

## 条码描述语言

| 语法 | 含义 |
|------|------|
| `*4 2 100 50` | 伪操作：定义字模 4（Code 39），后三个数为参数 |
| `$HELLO` | 以 `$` 开头的行是**字面文本**，不查符号表 |
| `HELLO` | 不带 `$` 的行按符号名查表；未定义则报 `UD undefined` |
| `*0 5` | 伪操作：以码 5 结束当前页（可省略，解释器自动补页） |

## 快速验证

```
$ cat bc.txt
*4 2 100 50
$HELLO
*0 5

$ palbart bc.txt          # 静默退出 0
$ cat bc.lst
      *4 2 100 50                          Page 1
    1        0004  *4 2 100 50
      00004  0152
    2              $HELLO

      No detected errors
      No links generated
$ ls -l bc.bin
-rw-r--r-- 1 user user 256 bc.bin
```

把未定义符号写进去，解释器会报诊断并以退出码 1 结束：

```
$ printf '*4 2 100 50\nHELLO\n*0 5\n' > bad.txt
$ palbart bad.txt
      2 detected errors
$ grep -E '^(UD|ND)' bc.lst
UD undefined      ^
ND no $ at EOF
```

以上正是本包消费者测试（23 条断言）的断言依据 —— 零网络、零渲染器、零设备节点。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 2.14 | `palbart/2.14` | 已适配（aarch64） |

## 授权

GPL-3.0-or-later（GNU barcode）。
