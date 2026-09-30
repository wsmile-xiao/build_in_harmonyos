# DRAFT: wordplay 9.0.1 —— C 程序链接 C++ 库（ICU）的三个适配形态

> 触发事件：wordplay 9.0.1 HarmonyOS PC 适配（archives/w/wordplay/9.0.1），Windows 宿主交叉验证实测。

## 症状（三条，同一次适配中先后出现）

1. `undefined symbol: std::__n1::...`（C 程序用上游 makefile 链接 ICU 静态库时，缺 C++ 运行时且顺序无法注入）。
2. ABI 检查报 `DT_NEEDED ... unexpected: ['libc++_shared.so']`，被误判为外来库。
3. Windows 交叉宿主上 test_package 执行 `python ohos_abi_check.py ...` 报 `The filename, directory name, or volume label syntax is incorrect.`。

## 根因

1. 上游 makefile 把 `-licuio -licui18n -licuuc -licudata` 写死在链接命令末尾。ICU 是 C++
   库，C 编译器驱动链接时 `-lc++` 必须排在 ICU 静态库**之后**；make 变量（LDFLAGS 等）
   只能出现在目标文件之前，尾部插槽无法注入。
2. OHOS clang 的 C++ 程序默认动态链接 `libc++_shared.so`——这是 OHOS 系统 C++ 运行时
   （/system/lib64），与 HNP 自带 cmake/ninja 同形（opencsg-1.8.2、E630 先例），
   不是 glibc/host 库。
3. `shlex.quote` 在 Windows 路径上产生 `'C:\...'` 单引号形式，cmd/pwsh 不识别。

## 修复

1. 配方 build() 绕过 make，直接驱动与 makefile 等价的单条编译链接命令，完全控制链接序：
   `obj → icuio → icui18n → icuuc → icudata → c++ → m/pthread/dl`（编译器来自
   `tools.build:compiler_executables`）。
2. `ohos_abi_check.py` 的 `ALLOWED_NEEDED` 白名单加入 `libc++_shared.so`；
   不静态打入 libc++（与 libc++_shared 共存有 E-OHOS-libcpp 弱符号双实现风险，且无必要）。
3. test_package 的 `self.run` 用双引号拼接 `'"exe" "arg"'`，路径不含引号字符时
   对 cmd/pwsh/POSIX sh 都安全。

## 验证

wordplay/9.0.1，Windows 宿主 + OHOS clang 15 交叉（profile fathom-local），
icu4c/78 二进制取自 ohpcd 远端：`conan create` rc=0；
ohos_abi_check A1-A9 本机实跑 9/9 PASS；
`DT_NEEDED=['libc++_shared.so', 'libc.so']`。

## 真机迭代发现（W5 shadow CI，3 轮修复后 100% 通过）

1. **词表全大写断言陷阱**：words721.txt 是全大写词典，wordplay 把输入大写化后输出
   （`sotp` → `POST/SPOT/STOP`）。基于源码阅读预设的小写断言（grep -qx "stop"）全部失败；
   anagram 校验必须大小写折叠（`tr 'A-Z' 'a-z'`），词匹配用 `grep -i`。
2. **`-i` 选项上游无行为**：真机实测 `-i` 与无 `-i` 输出逐字节相同（silent/header 模式
   diff 均空），断言只能降级为"选项被接受 + 输出仍为合法 anagram"，不能断言内容变化。
3. **隔离 job 环境两个坑（已有通用草稿，此处仅记 wordplay 的症状变体）**：
   a) 新 job 的隔离 conan-home 无 ohpcd remote → L0i 直接报
   `ERROR: Remote 'ohpcd' doesn't exist` → `registry_unreachable`（比
   DRAFT-shadow-ci-isolated-conanhome-missing-ohpcd-remote 记录的"错配方构建失败"
   更早一步，在门禁阶段即失败）；b) job env.sh PATH 缺 `/data/service/hnp/bin` →
   **KC 门禁阶段** `build_and_test.sh:980: permission denied: bash`（zsh 报
   permission denied 而非 127，区别于 opencsg 草稿的构建期 cmake 127）。
   二者均为环境操作，不动配方。
4. **HMDFS 不可执行诊断法**：手动复现二进制行为时，conan 缓存包目录（/storage，HMDFS）
   不能直接执行（`inaccessible or not found`），需复制到非 HMDFS 分区
   （/data/storage/el2/base/haps/entry/files/）再跑——与铁律 5 一致。test_package 本身在
   CI 内可执行（conanrun 环境），不受影响。

## 适用范围

任何"纯 C 程序 + ICU（或其他 C++ 库）静态链接"的包；任何在 Windows 宿主上做
OHOS 交叉 conan create 且 test_package 需要调用解释器/工具的配方。
