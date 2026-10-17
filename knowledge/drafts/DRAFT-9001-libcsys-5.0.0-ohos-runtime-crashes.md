# DRAFT-9001 — libcsys 5.0.0 HarmonyOS 运行时崩溃群

**状态**: DRAFT（待审）  **严重度**: 🔴 3  **软件**: libcsys 5.0.0（Qt6 CMake 库）
**适用阶段**: runtime / testing  **平台**: HarmonyOS/OHOS aarch64

## 现象

`conan create` 编译阶段**零报错**，`libcsys.so` 正常产出；但一旦运行消费者程序：

```
== CpuInfo ==
cores: 20
freqs n= 0 QList()          # /proc/cpuinfo 无 "cpu MHz" → 频率列表为空
...
== InfoManager ==
cores: 20
（EXIT=139 SIGSEGV）        # InfoManager::update() 内崩溃
```

`Power` 单独测试时现象更隐蔽——**main 跑完、退出瞬间**才崩：

```
$ ./t            # 只做 { Power p; } + 打印
constructed Power
（EXIT=139）      # 析构器内 SIGSEGV
```

## 根因（三处相互独立的缺陷）

1. **/proc 字段缺失 → 空表越界**
   `CpuInfo::updateInfo()` 只在 `/proc/cpuinfo` 出现 `cpu MHz` 行时才 append 频率；
   OHOS `/proc/cpuinfo` 只有 `processor/BogoMIPS/Features/...`，**没有 `cpu MHz`**
   （实测 `grep -c "cpu MHz" /proc/cpuinfo` = 0）。于是 `getCPUFrequencies()` 返回空
   `QList`，而 `InfoManager::update()` 仍按 `for i in 0..nCPU-1` 读 `xFrequencies[i]`。
   Qt6 release 构建把 `Q_ASSERT(i < size())` 编译掉 → 直接越界 → SIGSEGV。

2. **容器析构循环条件写反**
   ```cpp
   Power::~Power() {
       while (providers.empty())      // ← 应为 !providers.empty()
           delete providers.takeFirst();
   }
   ```
   无 systemd-logind / ConsoleKit 时 `providers` 为空 → 条件为真 → 空表 `takeFirst()`
   越界。OHOS 无这些 D-Bus 服务，**必然触发**。

3. **系统调用返回值语义误用**
   ```cpp
   char *hostname = new char[256];
   int size = gethostname(hostname, 256);   // 成功返回 0，不是长度！
   return QString::fromLatin1(hostname, size);   // size=0 → 恒空串
   ```
   实测 C 程序 `gethostname()` 返回 `rc=0 name='localhost'`，而
   `SystemInfo::getHostname()` 返回 `""`。

## 可复用处置

1. 凡"按 /proc 字段填充的列表"，读取端必须越界安全：
   ```cpp
   mCpuFrequencies[i] << xFrequencies.value(i, 0.0);   // 或先 if (i < size)
   ```
2. 容器析构循环条件一律 `while (!c.empty())`；涉及 D-Bus 提供者的析构器必须能在
   空容器上安全遍历。
3. 系统调用返回值不得当长度/大小用：`gethostname` 成功返回 0；缓冲区先零初始化再
   `QString::fromLatin1(buf)`（靠 strlen）。
4. **测试必须真实运行二进制**（R34）：这类缺陷编译期不可见，唯有运行期退出码暴露。
   本包 test_package 用 `self.run()` 跑真实二进制并统计 `assertions=N failures=M`。

## 判定要点

- 与普通"链接期 undefined reference"区分：本条是**编译链接全过、运行期才崩**。
- 与"缺 D-Bus 服务导致返回空"区分：返回空是**预期降级**（只要不崩即可）；崩溃才是 bug。
- 空 `QList` 上 `operator[]` 在 Qt6 release 下不抛异常、不 assert，**静默读越界**——
  不能依赖调试构件的断言来发现问题。

## 实证

libcsys 5.0.0 首适配：patch `0001-fix-runtime-crashes.patch` 修复三处后，
`conan create`（test_package）实测 `libcsys test summary: assertions=41 failures=0`，
退出码 0；修复前同一二进制 EXIT=139。

## 待办

- 提升为正式 E 条目；补充 `similar_to` 到已有 procfs/runtime 相关条目。
- 可考虑把"OHOS /proc 字段缺失清单"独立成一条平台真理条目。
