# E568 — 2000 年代 config.guess 识别不了本平台，autotools configure 直接失败

## 错误特征
```
checking host system type... Invalid configuration `unknown-unknown-linux-gnu':
machine `unknown-unknown' not recognized
configure: error: cannot guess build type; you must specify one
```
辅助证据：`/usr/bin/uname -p` 输出 `unknown`（本平台 uname 不返回 CPU 型号）。
若工程用 AM_PATH_XML2 之类宏，还会接着出现
`configure: error: XML2 not found`（因为 AC_TRY_RUN 在交叉编译下无法运行）。

## 触发条件
- 构建系统: autotools（携带 2006~2010 年版 config.guess/aclocal.m4）
- 阶段: configure
- 平台: HarmonyOS PC（aarch64-linux-ohos），或任何 uname -p 不返回 CPU 名的交叉目标

## 根因分析
老 config.guess 依靠 `uname -p` 判 CPU、`uname -s` 判内核，本平台 `uname -p` 返回 `unknown`，
于是拼不出合法 triplet，configure 直接终止。这与工具链无关，加多少 -I/-L 都无效。
同期的 aclocal.m4 普遍用 `AC_TRY_RUN` 探测依赖（如 AM_PATH_XML2），交叉编译场景下
AC_TRY_RUN 不能运行目标程序，若宏没有提供可缓存变量兜底，同样会失败。

## 解决方案

### 推荐方案
1. 先查上游是否**同时提供 CMake（或 meson）构建**：有就走那条路，比修 autotools 便宜得多
   （dictconv 0.2 即如此：CMake 侧只需补 cmake_minimum_required，见 E567）。
2. 走 CMake 时，老式 FIND_PATH/FIND_LIBRARY 的绝对路径问题用 cache 变量注入解决（见 E569）。
3. 只有 autotools-only 的工程才考虑 `autoreconf -fiv` / `automake --add-missing` 重新生成
   config.guess（需要较新 autotools，且可能连带引入其他回归，须重点回归）。

### 禁止做法
- ❌ 手工编辑上游 config.guess 猜 triplet（脆弱、不可复核，且只解决第一个失败点）。
- ❌ 用 `--build=x86_64-linux-gnu --host=aarch64-linux-ohos` 硬顶而不验证产物
  （往往绕过第一个错误后在 AC_TRY_RUN 处再次失败）。

## 验证
```bash
sh config.guess                      # 能输出合法 triplet 才具备 autotools 可行性
./configure --host=aarch64-linux-ohos --prefix=$PREFIX && echo CONFIGURE_OK
```
走 CMake 路线时的等价验证：`cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=ohos.toolchain.cmake && echo CONFIGURE_OK`

## 关联条目
- 相关: E567（CMake 4 缺 cmake_minimum_required）
- 相关: E569（FIND_PATH/FIND_LIBRARY 硬编码路径的 cache 变量注入）
