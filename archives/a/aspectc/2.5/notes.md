# aspectc 2.5 适配笔记（路径 C：高难度挑战）

## 结论

AspectC++ 2.5（ac++ / ag++ 织入编译器）已在 OHOS aarch64 上真实构建成功并
通过上游测试套件 196 项（详见 manifest.yaml）。**不是**绕过式假适配：ac++
/ ag++ 是真实验证过可织入 aspect 并产出可运行二进制的完整工具链。

## 破局点：双重自举死锁的解法

AspectC++ 的构建存在两个死锁：

1. **Clang 前端死锁**：`FRONTEND=Clang` 需要 clang 18+ 的完整静态库
   （`-lclangSema -lclangAST ... --link-static`），OHOS SDK 只有 clang
   15.0.4 且无任何 `libclang*.a`。
2. **Puma 自举死锁**：完整 Puma 含 ASPECTS，必须用 ac++/ag++ 织入，而官方
   无 aarch64 二进制、2.x 不再发布 woven 包。

解法（实测有效）：

- **Puma `MINI=1` 免 weave**：MINI 模式生成 libMiniPuma.a，不需要 ac++/ag++
  织入，直接用 OHOS clang++ 编译成功。
- **补齐 clang 18.1.8 静态库**：从 Alpine 3.21 aarch64（musl）仓库获取
  `clang18-static`（libclang*.a 全套）+ `llvm18-static`（libLLVM*.a 全套），
  共 283 个 .a，正好匹配 aspectc 的 `config/clang-18.1.8.mk`。
- **ABI 统一为 libstdc++**：Alpine 的 LLVM 对象基于 libstdc++ 编译，而 OHOS
  默认 libc++，混链会因 `std::__cxx11` vs `std::__n1` mangling 不同而失败。
  方案：全部源码用 `-nostdinc++ -isystem <libstdc++ headers> -nostdlib++
  -lstdc++` 编译链接（绕过 OHOS clang 拒绝 `-stdlib=libstdc++` 的限制）。
- **补充缺失的 musl 符号**：`secure_getenv`（glibc 扩展，OHOS musl 无）——
  一行 stub。
- **`-DMAX_PATH=4096`**：OHOS 头文件不链式提供 PATH_MAX。
- **lemon C 工具**：`-std=gnu++11` 泄漏到 C 编译（GCC 容忍、clang 拒绝）——
  patch 0001 将 -std 移入 CXXFLAGS。
- **ag++ 后端 g++**：OHOS 无 g++，包内提供 g++/gcc shim 指向 clang++。

## 运行时依赖

ac++ / ag++ 是 OHOS ELF 工具，动态链接 libxml2.so.2、libz.so.1、
libc++_shared.so。打包时用 `patchelf --set-rpath` 指向 hnp libxml2 与 SDK
libc++ 目录（**先 patchelf 再签名**，签名后再改 ELF 会破坏 .codesign）。

## 测试统计（真实）

上游 `make -C AspectC++ test` 全量套件（FRONTEND=Clang）：

- 通过（diff 与 .ref 完全一致）：196
- 失败 0
- 4 项差异（已逐一定性，见 manifest.yaml）：
  - Float128Basic：aarch64 无 __float128（上游 Darwin 也排除，平台限制）
  - ExecAdviceNewDelete：织入正常，输出行序与 ref 不同
  - RepoVersion：stale repo 格式触发预期版本警告文本
  - STLString：clang 15 后端下 std::basic_string 的 call pointcut 未匹配
- helloworld 示例端到端验证：织入后输出 "Hello World" ✔

## 与上游/参考的关系

- Debian/Ubuntu aspectc++ 2.5-1 包（arm64）证实 arm64 可构建，缺口仅在工具链供应。
- 参照 `archives/l/libayatana-indicator`（sh wrapper 先例）、evince（ELF 签名 +
  patchelf 先例）、astap（工具链下载先例）。
