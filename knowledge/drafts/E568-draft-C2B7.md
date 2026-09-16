# E568 — 栈上结构体未初始化，免硬件路径把垃圾句柄交给清理函数导致 SIGSEGV

## 错误特征

程序在"无设备 / 演示模式"下**业务逻辑正常执行、输出正确，随后立即 core dump**：

```
$ dcled -n -e -m HELLO
HELLO
Signal 11 (core dumped)
$ echo $?
139
```

关键特征（用于与普通段错误区分）：

- 崩溃发生在**退出清理阶段**，不在业务逻辑里 —— stdout 上该打印的内容已经完整打印
- 退出码恒为 **139**（SIGSEGV），线程栈顶通常是清理/析构函数而非业务函数
- 与硬件是否连接**无关**：`-n`（nodev）路径同样必崩，因此它不是"设备没插好"类问题
- 在 Conan 里表现为 `ConanException: Error 139 while executing ...`，
  容易误判成"交叉编译产物不可执行"或"平台不支持"

## 触发条件

- 构建系统: 任意（本例为 plain makefile，与构建系统无关）
- 阶段: 运行/测试阶段（编译链接全部正常通过）
- 代码形态: 栈上声明结构体后**只取址、不做初始化**，且该结构体含句柄/指针字段：

```c
struct ledscreen maindisp;      /* 栈垃圾，handle 字段为任意值 */
...
disp = &maindisp;
```

- 运行模式: 程序存在"无设备/演示"分支（本例 `-n`），该分支下句柄从未被真正赋值，
  但退出路径**无条件**走到 `close_usbdev()`：

```c
static int close_usbdev(struct ledscreen *disp)
{
    libusb_release_interface(disp->handle, 0);   /* 垃圾 handle → SIGSEGV */
    ...
}
```

## 根因分析

栈上对象未初始化并不总是立即出问题 —— 只有当**未初始化字段被当作有效资源使用**时才发作。
本例中 `-n` 模式不打开设备，`disp->handle` 自始至终没被赋值，但清理函数不做判空：

1. `struct ledscreen maindisp;` 分配在栈上，内容为**上一帧残留的任意字节**，不是零
2. `disp = &maindisp;` 取址后，`disp->handle` 从未被写入
3. 程序结束 → 无条件调用 `close_usbdev(disp)`
4. `libusb_release_interface(disp->handle, 0)` 用垃圾指针解引用 → SIGSEGV

值得注意的反直觉点：**崩溃与"是否打开过设备"无关**。直觉上 `-n` 不碰设备就不会崩，
但清理路径不做判断；同样地，`-n` 恰好是全部自动化测试唯一能用的路径，
于是"编译成功、手工 `-h` 正常、一跑 `-n -m` 就 139"。

诊断手段按效率排序：

| 手段 | 命令 | 定位能力 |
|------|------|----------|
| 退出码对照 | 补丁前/后跑同一条命令比 `echo $?` | 139 → 0 即确证 |
| 调试器 | `gdb --args ./dcled -n -e -m HELLO` → `bt` | 直接给出 `close_usbdev` → `libusb_release_interface` 帧 |
| 内存检查 | ASan 重编译或用 valgrind 跑同一命令 | 报 uninitialized value used |
| 静态阅读 | 搜 `&<带句柄的结构体>` 的取址点，回查是否初始化 | 无需运行环境 |

## 解决方案

### 推荐方案

**在使用前把整个栈上对象零初始化**（一行，最小改动面）：

```diff
     struct ledscreen maindisp;
 
+    memset(disp, 0, sizeof(*disp));
     disp = &maindisp;
```

或等价地在定义处初始化：`struct ledscreen maindisp = {0};`

归零后 `disp->handle` 为 `NULL`，清理函数既有的判空逻辑即可正常短路，
`-n` 路径立刻从 exit 139 变为 exit 0。生成补丁须走工具管线，不要手写：

```bash
track-edit add <software> <version> <source-file>
refresh-patch --auto <software> <version>
```

**这条修复属于纯上游缺陷修复，不是平台适配**：不引入任何平台宏
（`#ifdef __OHOS__` 之类），在 Linux 上同样是正确行为，所以可以无条件打进补丁，
无需在 PR 中论证平台例外（对比 R8 对平台宏的默认禁止）。

### 禁止做法

- ❌ **为绕过崩溃让 `-n` 模式提前退出或跳过清理**
  例如 `if (nodev) return;` / `if (nodev) exit(0);`。
  这会掩盖真实缺陷，并让 `-n` 模式彻底失去验证价值 —— 而它正是全部自动化测试依赖的路径；
  真实设备路径上的同类问题依然存在。属掩盖症状而非修复，PR 会被要求整改。

- ❌ **把崩溃标记为可忽略 / 伪造通过**
  例如 catch 掉 `Error 139` 继续、或在 `.ci-result.json` 里直接写通过。
  验证门禁 FAIL 时禁止标 success（R7）；伪造结果会被 CI 审计判定测试造假，PR 拒收。

## 验证

```bash
# 1) 补丁前后的退出码对照（最直接的确证）
dcled -n -e -m HELLO ; echo "rc=$?"
#   补丁前: 打印 HELLO 后 rc=139
#   补丁后: 打印 HELLO 后 rc=0

# 2) 补丁干净应用
cd <source_dir> && git apply --check patches/0001-init-ledscreen-maindisp.patch && echo apply_rc=0

# 3) 同类无限模式不再提前崩溃（按超时窗口收口）
timeout 20 dcled -n -e --test > /dev/null 2>&1 ; echo "rc=$?"   # 补丁后 124（等到超时），非 139

# 4) 整包回归
conan create . --profile:build=default --profile:host=ohos-aarch64
```

## 关联条目

- 相关: E249（同类运行期崩溃模式的诊断入口）、E040（交叉编译产物运行期异常）、E462
- 原则: P005、P012
- 实例: dcled 2.2 适配 —— `-n -e -m HELLO` exit 139 → 一行 memset 修复后 exit 0，
  补丁 `patches/0001-init-ledscreen-maindisp.patch`
