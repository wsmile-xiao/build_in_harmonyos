# ILP32 时代 C 库在 OHOS LP64 (aarch64/bionic) 的类型宽度假设缺陷：wchar_t 与 unsigned long 混用、零长度 read 返回 -1

- **草稿 ID**: DRAFT-libuninum-2.7-lp64-ilp32-type-assumption-defects
- **来源**: libuninum 2.7 HarmonyOS PC 适配（numconv CLI 输入/输出各截断为单字符的定位与修复）
- **分类**: lp64 / portability / wchar / posix-read / cli-tool / consumer-test
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **签名 1（输出截断）**：CLI 工具对多字符结果**每行只输出第一个字符**；库 API 层面同一转换返回完整字符串。
  - 复现：`printf "6453\n" | numconv -f Western -t Arabic_Western` 只输出 `٦`（应为 `٦٤٥٣`）
  - 库级对照：`IntToString(&val, NS_ARABIC_WESTERN, NS_TYPE_STRING)` 逐码点打印 `0666 0664 0665 0663` 完整
- **签名 2（输入截断）**：CLI 工具对多字符输入**每行只读入第一个字符**（`read(fd, buf, 0)` 依赖平台）。
- **共性**：库的单元/API 级测试全过，CLI 端到端却"每行一个字符"——缺陷藏在 CLI 边界层的类型/系统调用假设上，而非转换逻辑本身。

## 根因

libuninum 是 2009 年（ILP32 时代）的代码，在 aarch64 LP64 环境下有两个隐含假设失效：

1. **`wchar_t` 与 `unsigned long` 宽度假设**：uniio.c 的 `putu8s(wchar_t *str, FILE *)`/
   `fputu8(wchar_t c, FILE *)` 按 4 字节步进读字符串；而 numconv.c 按
   `extern void putu8s(UTF32 *, FILE *)`（`UTF32 = unsigned long`，aarch64 上 8 字节）
   传入 UTF32 数组。LP64 下 `wchar_t`(4B) ≠ `unsigned long`(8B)，循环在第一个码点的
   **高 4 字节 0** 处即当作 `L'\0'` 终止——输出恰好只剩首字符。上游在 ILP32
   （unsigned long == wchar_t == 4 字节）上永不触发。
2. **`read(fd, buf, 0)` 返回值假设**：UTF8in 的尾字节读取循环
   `do { BytesRead = read(fd,&c[BytesSoFar+1],BytesNeeded-BytesSoFar); ... } while (BytesRead > 0 || BytesSoFar < BytesNeeded);`
   在 `BytesNeeded=0`（ASCII 字符）时仍执行一次 `read(fd, buf, 0)`。glibc 返回 0，
   循环退出；**bionic 返回 -1**，`BytesSoFar` 变为 -1，循环条件继续成立并过量吞读
   后续字节，直到把整行余下输入全部吃掉——下一次读取直接 EOF，每行只读到首字符。

> 通用规律：ILP32 时代源码中 `long`/`wchar_t`/指针混用的"4 字节字符"假设、以及
> `read()/write()` 零长度调用的返回值假设，在迁移到 LP64 + bionic 时会同时失效，
> 且症状（CLI 每行单字符）与根因（类型/系统调用）分离，极易误判为平台 execve 或
> 文件系统问题。

## 最小修复方案

在 `archives/l/libuninum/2.7/**` 范围内（补丁均为 unified diff，单一职责）：

1. **0003-uniio-putu8-utf32.patch**：`fputu8`/`putu8s` 形参与局部指针从
   `wchar_t` 统一为 `UTF32`（与唯一调用方 numconv.c 的 extern 声明一致，函数体
   本就按 UTF-32 码点处理）：
   ```diff
   -fputu8(wchar_t c,FILE *fp)
   +fputu8(UTF32 c,FILE *fp)
   -putu8s(wchar_t *str,FILE *fp)
   +putu8s(UTF32 *str,FILE *fp)
   ```
2. **0002-uniio-utf8in-zero-read.patch**：仅在实际需要尾字节时读取，读取出错即停：
   ```diff
   -  do {
   -    BytesRead = read(fd,(void *) &c[BytesSoFar+1],(size_t) (BytesNeeded-BytesSoFar));
   -    BytesSoFar += BytesRead;
   -  } while (BytesRead > 0 || BytesSoFar < BytesNeeded);
   +  while (BytesSoFar < BytesNeeded) {
   +    BytesRead = read(fd,(void *) &c[BytesSoFar+1],(size_t) (BytesNeeded-BytesSoFar));
   +    if (BytesRead <= 0) break;
   +    BytesSoFar += BytesRead;
   +  }
   ```
3. **消费者端到端用例**（test_package/test_cli.sh）：以被测包安装的 numconv
   （`dependencies` 元数据 + `cpp_info.bindirs` 定位，不依赖 PATH）做完整
   输入→转换→输出断言，直接验证两个补丁的可用性——修复前该用例必失败。

## 实际验证结果

- **修复前**：`numconv` 每行只输出/读取首字符（真机 10.62.178.77 实测复现）。
- **修复后**：真机 `conan create` 全流程通过；test_package 19 项 API 断言 + 1 项
  CLI 端到端用例（Western→Arabic_Western 输出 4 字符 8 字节 + 反向转换）全部通过
  （`test_cli.sh: numconv end-to-end conversion OK`）。
- 定位方法（可复用）：**库级探针与 CLI 端到端分离验证**——先用库 API 逐码点打印
  转换结果（证明转换逻辑正确），再用 CLI 管道用例复现截断（证明缺陷在边界层），
  最后用 `UTF8in` 单函数探针逐字节打印（证明输入层无误）→ 收敛到输出层类型混用。

## 适用范围

- ILP32 时代（约 2000-2012 年）的 C 库，源码中 `wchar_t`、`unsigned long`、指针
  宽度混用表达"码点/宽字符"语义；
- 在 OHOS（aarch64 LP64 + bionic）上构建，库 API 正常但自带 CLI 工具出现
  每行单字符读/写；
- 直接使用 `read()`/`write()` 并依赖"零长度调用返回 0"假设的代码；
- 消费侧需要同时交付库与 CLI 工具、需要端到端验证补丁效果的包。

## 非适用边界

- 库 API 本身就截断/崩溃的（缺陷在核心逻辑，不在边界层）——先按 API 用例定位；
- 源码已使用 `uint32_t`/`char32_t` 等显式宽度类型、无 long/wchar_t 混用的库；
- 依赖 wchar_t 语义但整体未适配 locale 的宽字符 API（`fgetws` 等）问题——那是
  locale 缺失类问题，不是类型宽度问题；
- `read(fd, buf, n)` n>0 的部分读（短读）处理缺陷——本条目只覆盖零长度调用假设。

## 查重差异

- 知识库 540 条（E001-E540）中无 wchar_t/UTF32/LP64 类型宽度、无零长度 read
  假设相关条目（按 wchar/UTF32/unsigned long/ILP32/类型宽度/bionic 关键词查重）。
- 与 E 系"平台行为差异"类条目主题相邻，但本条目给出的是**源码级类型宽度缺陷**
  的错误签名、二分定位法（库级探针 vs CLI 端到端）与两个可复用补丁模式。

## 关联交付

- 本草稿与 `archives/l/libuninum/2.7/**` 属于同一 libuninum 交付范围
  （分支 `feat/libuninum-2.7`，test_package 19+1 用例全过）。
- 正式 E 编号由知识库主编审核后分配。

## 禁止模式

1. **把 UTF32 缓冲强转成 wchar_t\* 去适配旧签名**：
   ```c
   /* ❌ 错误：强转掩盖宽度差，LP64 上继续截断/越界 */
   putu8s((wchar_t *)utf32_buffer, fp);
   ```
   - 后果：8 字节码点被按 4 字节切片，仍会在高半字 0 处提前终止，且可能越界读。
2. **用"多读一次再回退"的方式绕过零长度 read**：
   ```c
   /* ❌ 错误：read 0 字节探测 EOF/阻塞语义，在 bionic 上不可移植 */
   if (read(fd, &ch, 0) == 0) { /* assume no-op */ }
   ```
   - 后果：返回值平台相关（glibc 0 / bionic -1），逻辑在两个平台行为分裂。

## 推荐模式

```c
/* ✅ 正确：边界层类型与调用方契约对齐（显式宽度类型），零长度读取用守卫消除 */
void putu8s(UTF32 *str, FILE *fp)   /* 与调用方 extern 声明一致 */
{
  UTF32 *ptr = str, c;
  while ((c = *ptr++) != 0) fputu8(c, fp);
}

while (BytesSoFar < BytesNeeded) {              /* 只在需要时读 */
  BytesRead = read(fd, &c[BytesSoFar+1], (size_t)(BytesNeeded - BytesSoFar));
  if (BytesRead <= 0) break;                    /* 0 与 -1 都终止 */
  BytesSoFar += BytesRead;
}
```

消费侧（test_package）端到端断言模式：

```python
# ✅ 正确：用 dependencies 元数据定位被测包 CLI，做真实端到端断言
dep = self.dependencies[self.tested_reference_str]
numconv = Path(dep.package_folder, dep.cpp_info.bindirs[0], "numconv")
self.run(f'sh "{script}" "{numconv}"', env="conanrun")
```

## 关联原则

- P010：尊重上游逻辑，补丁最小化且单一职责（一个补丁只修一类宽度/系统调用假设）
- P020：消费者测试必须验证真实使用场景——库级断言全过不等于 CLI 可用，端到端
  用例是发现本类缺陷的唯一手段

## 相似条目

- 无直接相似条目（查重见上）；E 系"平台行为差异"类条目为本条目的上位主题。
