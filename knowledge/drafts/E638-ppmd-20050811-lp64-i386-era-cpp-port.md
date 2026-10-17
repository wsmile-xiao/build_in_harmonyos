# E638 — i386 时代的 C++ 压缩器移植到 aarch64/LP64 的三类系统性雷区（ppmd/PPMd-I 实测）

> 草稿状态：任务侧留痕，最终编号以知识库主编确认为准（任务侧取号 E638，2026-09-21）。
> 来源任务：feat/ppmd-20050811（PPMd variant I，public domain，Debian/FreeBSD 打包链）。

## 结论

FreeBSD `ONLY_FOR_ARCHS=i386`（或 portfile 等价标注）是**移植前哨**：它往往同时
预言两类运行期雷区与一类编译期雷区。ppmd 20050811 在 aarch64/LP64 上的全部
功能缺陷都被该标注命中，三类雷区的机理与修法如下。

## 雷区一：自定义子分配器的"粒度=12"假设（段错误）

PPMd-I 的 `SubAlloc.hpp` 以 `enum { UNIT_SIZE=12 }` 为分配粒度，并假设落位在
单元内存上的结构是 4+4+4=12 字节（`BLK_NODE{DWORD Stamp; BLK_NODE* next;}`
+ `MEM_BLK{DWORD NU;}`，`PPM_CONTEXT` 同理 4+指针+指针）。i386 下
`PPM_CONTEXT`=4+4+4=12=UNIT_SIZE、`MEM_BLK`=12、`STATE`=2+4=6（每单元 2 个
状态，`Stats[i]` 与 `(NumStats+2)>>1` 一类的"2 状态/单元"寻址全部依赖它）。
LP64 下指针 8 字节：`PPM_CONTEXT`=4+8+8=20、`MEM_BLK`=Stamp(8)+next(8)+NU(8)=24、
`STATE`=10 —— 结构溢出单元边界，`pm+pm->NU` 步长错位，**编码立即段错误**
（实测 rc=139，产物 0 字节）。

修法（patch 0002）：按 `__LP64__` 把粒度提到 `3*sizeof(DWORD)`=24（MEM_BLK 的
自然尺寸），同时验证两个不变量：`sizeof(PPM_CONTEXT)`=20 ≤ 24（4 字节冗余）、
`2*sizeof(STATE)`=20 ≤ 24（"每单元 2 状态"寻址不变量保持）。配套把
`U2B(NU)=8*NU+4*NU` 改为 `UNIT_SIZE*NU`、`UnitsCpy` 改为按 UNIT_SIZE 逐字节
拷贝（原 3×DWORD 循环在粒度≠3×sizeof(DWORD) 的组合下会越界）。

## 雷区二：手写 carryless 区间编码器的 32 位回绕假设（解码首符号即失步）

`Coder.hpp` 的状态 `static DWORD low, code, range;` 在 i386 上是 32 位；算法
（Subbotin carryless rangecoder）**依赖 32 位回绕丢弃进位**：
`range=DWORD(-1)` 必须是 2^32-1，`ARI_ENC_NORMALIZE` 的 `(low ^ (low+range)) < TOP`
与 `-low & (BOT-1)` 的进位处理、`low <<= 8` 的高位丢弃，全部建立在 32 位字长上。
LP64 下 `DWORD`=unsigned long=64 位：`range` 初值变 2^64-1，`ariGetCurrentCount`
首次除法即得 0，**解码从第一个符号就失步**——实测文本 5375B 解出 6786B 乱码、
75B 小文件解出 NUL 开头 junk；同一失步二进制偶发侥幸一致（bin.dat 55744B 一度
IDENT，属数据巧合，不能当通过证据）。

修法（patch 0003）：`low/code/range` 与 `SUBRANGE{LowCount,HighCount,scale}`
钉死 `unsigned int`。注意这与雷区一的 `DWORD` 方向相反——分配器需要 64 位
DWORD 来容纳指针尺寸，编码器需要 32 位来保持回绕语义，**不能全局 typedef 一刀切**。

## 雷区三：档案格式里裸写 `DWORD` 的字段（头长随字长漂移）

`ARC_INFO{DWORD signature,attrib; WORD info,FNLen,time,date;}` 用
`fwrite(&ai,sizeof(ai))` 整结构体落盘：LP64 下头从 canonical 16 字节变 24 字节。
修法（patch 0004）：`signature/attrib` 钉死 `unsigned int`，头保持 16 字节
（od 实测 `8f af ac 84 | ... | FNLen` 与 ppmdi1 规范布局逐字节一致）。
判据：`od -A d -t x1 <archive> | head -2` 的前 16 字节必须是
magic(4)+attrib(4)+info(2)+FNLen(2)+time(2)+date(2)。

## 附带：C++11 UDL 编译错误（新 clang 上的确定性失败）

`"...%c, "__DATE__"\n"` —— 字符串字面量紧邻 `__DATE__` 会被 C++11 词法成
**用户自定义字面量后缀**（`operator""__DATE__`），clang 15 直接报
`no matching literal operator`。空格必须加在**字面量与宏之间**
（`" %c, " __DATE__ "\n"`）。老源码迁移的第一轮编译就会撞上（patch 0001）。

## 附带：平台 smoke 探针与老 CLI 的发现旗标契约

平台 L2 探针只试 `--version/--help/-V/-h` 并要求 rc=0；上游 CLI 用
`return -1`（255）应答一切未知输入。与 libgig「只实现小写 -v」同族
（notes/defects/ci-and-w3.md 第 5 类）。既定解法（patch 0006）：旗标为
**唯一参数**时接受标准发现旗标并退出 0，其余调用路径（含无参 255）保持
上游行为不变——不加参数解析副作用，不改变既有语义。

## 验证判据（可直接执行的命令）

```sh
# 1) 编译（两处都要零 error）
clang++ -c -O2 PPMd.cpp && clang++ -c -O2 Model.cpp && clang++ -O2 -o ppmd PPMd.o Model.o
# 2) 发现旗标（rc 必须为 0）
./ppmd --version; echo $?; ./ppmd -h >/dev/null; echo $?
# 3) 上游行为保持（无参用法错误必须仍是 255）
./ppmd; echo $?
# 4) 通往返矩阵（编码→解码→逐字节一致；档案名是"替换扩展名"而非追加）
printf 'text...' > t.txt && cp t.txt t.ref && ./ppmd e -s t.txt && rm t.txt \
  && ./ppmd d -s t.pmd && cmp t.ref t.txt && echo IDENT
# 5) 档案头 canonical 16 字节（magic 84ACAF8F 小端 + 属性 + info + FNLen）
od -A d -t x1 t.pmd | head -2
# 6) 大文件压力（触发 GlueFreeBlocks/模型恢复路径）
#    6.9MB 生成文本 → 596473B（约 0.69 bpb），解码逐字节一致
```

实测（2026-09-21，HarmonyOS aarch64，clang 15.0.4，GNU make 4.4.1）：
补丁链后 4 文件 × 5 参数组（默认/-o16 -m64/-o2 -m1/-r1 -o8/-r2 -o4 -m32）
全部 e=0 d=0 IDENT；test_package 23 断言全 PASS；`bin/ppmd` sha256
`76fcdea0012d087a24521a13159b23032f202175cb0d0557d0498c50c2ef45f0` 与纯净树
补丁链构建逐字节一致。

## 排查路径（给下一个任务）

1. 移植标注前哨：FreeBSD ports `ONLY_FOR_ARCHS`、Debian `Architecture: i386`。
2. 源码体检顺序：`grep -n "UNIT_SIZE\|enum {" **/SubAlloc*`（分配器粒度）→
   `grep -n "DWORD low\|unsigned long" **/*oder*`（编码器状态字长）→
   `grep -n "fwrite(&\|sizeof(ai)" *.cpp`（裸结构体落盘）→
   `grep -n '"__DATE__\|"__TIME__\|"__FILE__' *.cpp`（UDL 词法）。
3. 失步定位技巧：给 encode/decode 循环加"每 N 符号打点"插桩对比 ns 序列；
   首符号即错优先查 range 初值与 `ariGetCurrentCount` 的除法字长。
