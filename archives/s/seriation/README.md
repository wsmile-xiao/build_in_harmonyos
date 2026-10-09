# seriation

`cfm_seriation` —— 用**模拟退火**把蛋白质相互作用网络排成一维序列，
使相邻节点之间的相互作用尽量密集（能量最小化）。

## 输入：CFM 边表

每行两个节点名表示一条边：

```
n1 n2
n2 n3
n3 n4
n4 n1
n1 n3
n2 n4
```

## 用法（注意：没有横杠）

参数解析器取 `argv[x][0]` 作选项字符、`argv[x][2:]` 作值，所以是 `f=...`
而不是 `-f ...`：

| 参数 | 含义 | 默认 |
|---|---|---|
| `f=` | 网络文件路径 | 必填 |
| `o=` | 读入已有初始序 | 无 |
| `i=` | 等温步数 | 100 |
| `m=` | 交换步数 | 100 |
| `c=` | 降温系数 | 0.4 |
| `a=` | alpha 权重 | 1.0 |
| `p=` | 初始温度百分比 | 0.01 |
| `s=` | 随机种子 | `time(NULL)` |
| `P` | 画图（需 gnuplot） | 关 |
| `v` | 生成视频帧 | 关 |
| `h` | 打印帮助后**退出码 1** | — |

## 快速验证

```
$ cfm_seriation f=mini.dat s=42 i=2 m=2
...
Reading file...
	Proteins: 4
	Interactions: 3
Applying random order...
Saving initial order...
INITIAL Energy: 12
Ordering...
100% [====...]
FINAL Energy: 12
Saving final order...
Done!

$ ls -d mini_*
mini_2026-10-04_04h14m38s
$ ls mini_2026-10-04_04h14m38s
energy.dat  final_order.dat  initial_order.dat  result.txt
```

输出目录名带时间戳，所以自动化流程应按 `<基名>_<YYYY-MM-DD_HHhMmMmSs>`
的正则形状去匹配，而不是写死目录名。

**定种子完全可重复**：`s=42` 连跑三次，INITIAL / FINAL Energy 逐次一致。
这正是本包消费者测试里最强的一条断言（24 条中的一条）。

## 范围

本包**不含**原 tarball 里 6 个物种的演示数据集（合计约 35MB），
也**不含** `-P` 画图所需的 `/usr/share/cfm-seriation/etc/matrix.gnu`。
绘图后端由调用方决定，核心排序逻辑不依赖 gnuplot。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 1.0 | `seriation/1.0` | 已适配（aarch64） |

## 授权

GPL-3.0-or-later。
