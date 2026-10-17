# draft-pd-syslog-0.1-pd-plugin-syslog-interpose-test

> Status: **Draft**（待审核 promote）| severity: `2` | category: `test|pd` | Updated: 2026-10-04
> 对应: `knowledge/drafts/DRAFT-pd-syslog-0.1-pd-plugin-syslog-interpose-test.kv`

---

**匹配关键词**：dlopen, RTLD_NOW, -rdynamic, interpose, symbol interposition, syslog, openlog, closelog, /dev/log, syslogd, m_pd.h, t_symbol, s_, PDINSTANCE, gensym, class_new, class_addanything, pd_new, floatinlet_new, getbytes, freebytes, atom_string

## 症状

要测的库是 Pure Data 插件 `[syslog]`：它唯一可观测的副作用是调用 libc `syslog(3)`。而 HarmonyOS PC 上：

- 没有 syslogd，`/dev/log` 不存在；
- musl 的 `syslog()` 在 `socket()/connect()` 失败时**静默返回**，不报错、不 abort。

于是「发一条消息然后去日志里找它」的测试写不出来——不是被测代码有缺陷，是测试设计与平台能力不匹配。

同时，因为插件是 Pd `dlopen()` 的、没有任何可链接的库，测试必须自己提供 Pd 运行时，写 shim 时又踩到 `m_pd.h` 的两个坑：

```text
pd_syslog_test.c:128:6: error: function cannot return function type 'int (t_method)' (aka 'int (void (*)(void))')
    note: expanded from macro 'class_addanything'
    note: `#define class_addanything(x, y) class_addanything((x), (t_method)(y))`
pd_syslog_test.c:131:28: error: use of undeclared identifier 'fn'
pd_syslog_test.c:251:33: error: too many arguments to function call, expected 0, have 1
    void *obj = nm((void *)sel);
                     ^~~~~~~~~~~
```

## 根因

**① 拦截点选在 libc 三个入口，而不是日志内容。**
动态符号查找序里**可执行文件优先于 libc**，所以测试可执行文件只要自己定义 `openlog` / `syslog` / `closelog`，插件对这些符号的未定义引用就会绑定到测试的定义。据此记录 ident/option/facility、priority、完整格式化文本、close 次数，断言就落在「插件实际转发了什么」上。

选这三个函数而不是只拦 `syslog`，是因为 `openlog()` 在 musl 里是惰性的——只记录 ident，**不建立连接**——所以 ident 这条信息只有在这里才拿得到；而 `closelog()` 则是析构行为的唯一证据。

**② `m_pd.h` 的 `s_` 有两个互斥分支。**

| 目标包的编译宏 | `m_pd.h` 里的 `s_` | 后果 |
|---|---|---|
| 未定义 `PDINSTANCE`（Pd library template 只加 `-DPD -DVERSION`） | `EXTERN t_symbol s_pointer, ..., s_;` — 普通全局**结构体** | 业务代码里 `&s_` 就是取地址；shim **要**定义 `t_symbol s_;` |
| 定义了 `PDINSTANCE` | `#define s_ (pd_this->pd_s_)`，`pd_this` 展开为 `&pd_maininstance` | `s_` 是宏，shim **不应**定义该符号 |

写 shim 前必须确认目标包编译时到底有没有 `PDINSTANCE`，否则会撞上「符号多余」或「符号缺失」两种相反的失败。

**③ `m_pd.h` 带一个自引用的 legacy 宏。**
`#define class_addanything(x, y) class_addanything((x), (t_method)(y))` 的两个形参正好匹配这个宏的两个参数，所以在测试里写

```c
void class_addanything(t_class *c, t_method fn) { … }
```

时，**函数定义自身被宏改写**成 `void class_addanything((t_class *c), (t_method)(t_method fn))`，于是报 `function cannot return function type` + `use of undeclared identifier 'fn'`。处置是定义前 `#undef`。

**④ `t_newmethod` 的声明与真实调用不符。**
`m_pd.h` 声明 `typedef void *(*t_newmethod)(void);`（无参），但 Pd 实际调用类构造函数时**传创建 selector**。按声明的类型直接调会得到 `Too many arguments to function call, expected 0, have 1`；shim 里必须显式转成真实签名 `void *(*)(t_symbol *)` 再调。

**⑤ `gensym` 必须按名驻留。**
Pd 的 `gensym` interning 且不释放。shim 若每次调用发新的槽位，后续 `gensym()` 会覆盖插件已经存进 atom 的 `t_symbol *`，断言会在非确定性时刻失败。`pd-libdir/1.11` 实测过同类问题。

**⑥ `struct _class` / `struct _pd` 是不完整类型**，不能 `sizeof`；shim 用 `long` 字节数组充当再转型返回。

## 处置

把测试可执行文件本身做成「最小运行时」——`-rdynamic` 编译，它定义的符号进入 `.dynsym`，能被 `dlopen` 进来的插件解析：

1. **interpose libc 侧**：自己定义 `openlog` / `syslog` / `closelog` 并记录。
2. **Pd 侧 shim**：定义插件 `GLOBAL UND` 的 9 个符号（`gensym` / `class_new` / `class_addanything` / `floatinlet_new` / `getbytes` / `freebytes` / `atom_string` / `pd_new` / 全局 `s_`）；用 `class_new` 收到的 `size` 给 `pd_new` 分配（镜像真实 Pd）；`getbytes` 记录请求字节数，用来断言上游的缓冲区算术。
3. **`dlopen(plugin, RTLD_NOW)`**：让装载本身证明所有导入可解析。
4. **按真实 Pd 分发路径驱动**：`dlsym` 取 `<name>_setup` → 调用 → 用记录到的构造函数构造（传创建 selector）→ 通过 `floatinlet_new` 记下的 float 指针写 severity（模拟 Pd 的 float 消息）→ 调记录到的 anything 方法 → 析构。

`pd-syslog` 用这套方法落成 35 条断言，全部打在真实转发行为上：

- 四个数据文件（`syslog-meta.pd` / `syslog-help.pd` / `README.txt` / `LICENSE.txt`）随插件一起打包；
- `dlsym("syslog_setup")` 解析成功且 `dlsym("setup")` 为 `NULL`（Pd 先找 `setup`、回退 `<classname>_setup`）；
- 恰好注册一个名为 `syslog` 的类，首个变参是 `A_DEFSYM`，构造/析构齐备，`class_addanything` 注册了消息处理函数；
- 空 selector 构造 → `openlog("puredata", 0, LOG_USER)`；带名 selector → `openlog(该名字, …)`；
- severity inlet 落在对象自身存储内；未动过时默认 `LOG_NOTICE`，写入 `LOG_ERR` 后转发优先级随之改变；
- float+symbol 消息转发一次且文本为 `bang 42 hello`；缓冲区恰好申请 `strlen(消息)+1` 字节并被释放；
- 连续两条消息保持各自顺序与各自 severity；无 selector 时只转发 atom 文本；空消息在**分配之前**就被丢弃；析构恰好 `closelog()` 一次。

## 预防

- 测「唯一副作用是调用某个 libc 接口」的库时，先确认**该接口在目标平台上是否真的可用**。若目标平台缺守护进程、缺设备节点，或该接口静默失败（musl 的 `syslog()` 就是典型），就不要去读它的输出——改为在测试可执行文件里 interpose 该接口，断言转发内容。
- interpose 之所以可靠：可执行文件在动态符号查找序中**排第一**，优先于它依赖的任何共享库。这一招不限于 libc 函数，任何「插件/插件依赖的库函数」都能这样截获。
- 写「宿主运行时 shim」前先读宿主头文件里目标符号的**全部声明与宏**（不止看函数原型）：本次就撞上了自引用宏改名函数的坑，以及同名符号在两种编译宏下语义完全不同的情况。
- 头文件声明的函数指针类型（这里是 `t_newmethod` 的无参声明）**不等于**框架实际调用它的形式；以框架源码的调用点为准，shim 里显式转型。
- shim 的 `gensym` / `intern` 类函数必须实现驻留语义，不能图省事每次发新槽位——被测代码常把返回的符号指针存进数据结构。
