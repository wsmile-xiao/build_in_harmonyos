# E543 — 改变结构体布局的特性宏必须经 `cpp_info.defines` 下发

## 错误特征

库编译时定义了某个特性宏，消费者却没有；编译与链接都成功，运行期才以内存越界、
字段读到垃圾值或栈破坏的形式暴露：

```
fossa.h:537
#ifdef NS_ENABLE_IPV6
  struct sockaddr_in6 sin6;      /* 28 字节（含 sin6_flowinfo / sin6_scope_id） */
#else
  struct sockaddr     sin6;      /* 16 字节 */
#endif
```

真机 aarch64 实测该联合体的布局差：

```
$ ./sz_off     # 未定义 NS_ENABLE_IPV6
union=16 in6=28 sa=16
$ ./sz_on      # 定义 NS_ENABLE_IPV6
union=28 in6=28 sa=16
```

库按 `NS_ENABLE_IPV6` 编译、消费者按关闭状态预处理同一头文件时，
`union socket_address` 的 `sizeof` 与后续字段偏移两边不一致（28 vs 16）：
消费者按小布局分配/拷贝，库按大布局读写 ⇒ 越界。这类故障**不会**表现为编译错误。

## 触发条件

- 构建系统: 任意（Conan 配方 + 下游 CMake 消费）
- 阶段: compilation / runtime —— 只在有布局宏的公共头文件被两边不同宏预处理时发生
- 高发对象: 单头文件库与合并产物（amalgamated `.c`/`.h`），因为布局开关直接写在交付头里

## 根因分析

特性宏有两类语义：

1. **功能开关**：只决定符号是否存在，消费者与库不一致会表现为链接错误或运行时缺能。
2. **布局开关（ABI 宏）**：改变公共头文件中结构体/联合体的成员类型或大小。
   第 2 类被误当成第 1 类处理时，问题静默地转移到运行期。

配方最常见的疏漏是只把宏传给库的编译命令，忘了把它写进 `cpp_info.defines`。

## 解决方案

### 推荐方案：把布局宏集中定义并原样下发

```python
# 编进库的特性宏 = 下发给消费者的特性宏，同一份常量，杜绝两处不同
FEATURE_DEFINES = ("NS_ENABLE_COAP", "NS_ENABLE_IPV6", "NS_ENABLE_THREADS",
                   "NS_ENABLE_MQTT_BROKER", "NS_ENABLE_DNS_SERVER")

def build(self):
    defines = " ".join(f"-D{d}" for d in FEATURE_DEFINES)
    self.run(f"{cc} -O2 -fPIC {defines} -c {src}/fossa.c -o {src}/fossa.o")

def package_info(self):
    self.cpp_info.libs = ["fossa"]
    self.cpp_info.defines = list(FEATURE_DEFINES)   # ← 关键：ABI 宏必须下发
```

并在 `test_package` 用**编译期**断言把这条契约钉住：宏不下发就编译不过，
从而把「静默内存错误」升级为「构建立即失败」。

```c
static void test_socket_address_layout(void) {
  union socket_address sa;
  memset(&sa, 0, sizeof(sa));
  sa.sin6.sin6_family = AF_INET6;                 /* 宏未定义时无 sin6_family */
  CHECK(sizeof(sa) >= sizeof(struct sockaddr_in6));
}
```

### 回退方案：隐藏布局宏

若上游布局宏可以不出现在交付头文件中（改由内部头持有），可只导出稳定 API。
本例不可行：宏就写在 `fossa.h` 里，因此采用推荐方案。

### 禁止做法

- ❌ 只给库加 `-D`、`cpp_info.defines` 留空，指望消费者自己猜。
- ❌ 让消费者自行增删特性宏来「适配」，两侧布局立刻不一致。
- ❌ 用静态链接或 `-fcommon` 一类的链接期手段去「消除」表现，根因仍在。

## 验证

消费者视角做**反证编译**（真机 aarch64 / clang 15.0.4 实测）：同一份消费侧源码，
去掉宏必须立刻编译失败 —— 这就把「静默内存错误」变成了「构建立即失败」。

```sh
# 不带宏 ⇒ 报错（实测输出）
$ clang -fsyntax-only -I. tc.c
tc.c:61:11: error: no member named 'sin6_family' in 'struct sockaddr'; did you mean 'sa_family'?
   sa.sin6.sin6_family = AF_INET6;

# 带宏 ⇒ 通过
$ clang -fsyntax-only -DNS_ENABLE_IPV6 -I. tc.c
$ echo $?
0
```

上面这组反证编译在真机 aarch64 / clang 15.0.4 上实测：不带宏立刻报错、带宏 rc=0。
本次交付的 `test_package` 之所以能编译跑通，说明宏确实随包下发了；
但仅凭编译通过不足以区分是 `cpp_info.defines` 还是 CMakeDeps 的其它传递路径起了作用，
因此契约必须显式写在 `package_info()` 里，并由这条反证编译守住。

## 关联条目

- 相关: E530（X11 客户端库在消费者测试里用强类型重定位 + ABI 布局固定 —— 本条的增量在
  契约的另一侧：布局宏必须由配方经 `cpp_info.defines` 下发，否则消费者无从固定）、
  E429（同批 fossa 草稿：子串过滤器导致的用例数虚高）、E544（同批：外部 DNS 语义）
- 适用铁律: R34（test_package 必须真实调用库 API —— 本条给出「ABI 契约」这类
  真实断言的写法）

## 来源

- 软件/版本: fossa/2.1（`archives/f/fossa/2.1`）
- 上游: https://github.com/cesanta/fossa `fossa.h:537`
