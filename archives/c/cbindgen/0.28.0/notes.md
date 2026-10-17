# cbindgen 0.28.0：HarmonyOS PC 适配

任务 6784，分支 `feat/cbindgen-0.28.0`，依赖项路径 A。官方基线：`1f6f17ddab675671eab02c4dd7b7c7e69c5d11f8`。
上游为 Mozilla 的 Rust/Cargo 工具；平台 cpp 标签指向其 C/C++ 构建用途，不表示实现语言为 C++。
本包交付 cbindgen CLI、使用文档及 Cargo 所需私有运行库；不导出 Rust rlib 作为 C 库。

## 固定源码与依赖

- 源码：https://codeload.github.com/mozilla/cbindgen/tar.gz/refs/tags/v0.28.0；tag v0.28.0；commit a976056ef61e6fcf0162ae81ba57fb92c8dfb599。
- 源码 SHA256：`b0ed39dda089cafba583e407183e43de151d2ae9d945d74fb4870db7e4ca858e`；许可证 MPL-2.0。
- Rust 1.97.1 来自已合入 !8610 的官方 Conan 包；build context 用于编译，host/run context 支持 crate/workspace 的 cargo metadata。
- OpenSSL 3.5.6.1.1 为已发布 PIC 静态包，仅用于生成 Cargo 私有运行库。
  同名共享库位于 `libexec/cbindgen`；package_info 不向消费者全局注入该目录的 LD_LIBRARY_PATH。
- `cargo_launcher.c` 显式启动当前 Python 与 `rust_runtime.py`，在子进程内设置库路径后 exec Cargo/rustc，保持参数、退出码和 TLS 校验；
  当前 Conan 环境的 certifi CA bundle 通过 CARGO_HTTP_CAINFO 传入。
- OHOS 运行签名在构建目录或使用方的私有缓存完成；只复制并签名 Cargo、rustc 和 rustc_driver，
  不修改依赖 Conan 包，不将约300MB的Rust驱动重打入cbindgen。缓存以配方辅助脚本和依赖清单识别，
  用文件锁与目录原子发布避免并发观察到未完成状态；默认sysroot指向声明的Rust依赖，保留调用方覆盖。
- 随包包含 OpenSSL Apache-2.0 许可证：上游
  https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.6/LICENSE.txt，
  SHA256 `7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a`。
- 上游编译测试所需 Cython 3.0.2 从 PyPI 官方固定源码取得并核对 SHA256，仅用于测试。

## 原始失败与最小修复

1. 早期已签名环境中 rustc 可运行；Cargo 返回127，提示找不到 libssl.so/libcrypto.so。
   已验证 OpenSSL PIC 静态包可重链接为所需 DSO；最终通过 Cargo 启动器限制加载范围。
2. OHOS Rust 子进程启动 Python shebang 脚本失败或停滞。Cython 通过小型 C 启动器显式 exec
   当前 Python 和官方 cython.py，保留全部 Cython 编译校验。
3. 上游 body fixture 包含匿名 typedef 中的 C++ 方法；Clang 15 的
   -Wnon-c-typedef-for-linkage 被 -Werror 提升。仅上游测试环境抑制该诊断，其余错误照常失败。
4. 宏展开 fixture 原本要求 nightly 的 -Zunpretty；RUSTC_BOOTSTRAP=1 仅作用于测试命令，
   生产编译和消费环境不设置它。原始 Cargo.lock 和全部参考头文件均保持不变。
5. 无上游源码补丁。构建脚本显式声明归档类型、独立 Cargo/TMP 目录和 profile 的 C/C++ 编译器。
6. PR !9264 的远端CI #43268暴露原始Rust包缺少OHOS执行签名，`Cargo exec: Permission denied`。
   新缓存重新下载后，复制并chmod仍失败；仅签Cargo/rustc后Rust驱动加载失败；连同私有驱动签名后启动通过。
   配方现将签名准备纳入正常构建和消费入口，签名失败直接报错，并记录依赖文件构建前后哈希。

## 验证

环境：HUAWEI HAD-W32、OpenHarmony 6.1.0.115、aarch64；HNP SDK 26.0.0.18；
Clang 15.0.4；Conan 2.29.1；官方 profile OHOS/6.0、armv8、Release、libc++。
新增源码通过独立 HDC 队列传入该设备；所有构建、消费者输出均在任务私有目录。

- 构建：`cargo build --locked --release --bin cbindgen`。
- 上游：`cargo test --locked --release --lib --bins --tests -- --test-threads=1`，保留 C/C++/Cython 生成结果比对及编译；161/161 个可执行测试实例。
  其中 lib/bin 各2项（同一源测试在两个目标执行），depfile 3项、profile 7项、生成器147项。
- 唯一 Rust 文档代码块原标记 rust,ignore；其余代码块为 TOML。工具链未包含 rustdoc，
  该示例未执行，单列为1项上游忽略示例，不计为可执行测试通过。
- `test_package/test.py` 从安装包生成 C 与 C++ 头文件，执行18项断言：
  单文件与 Cargo crate 输入、depfile/symfile/verify、repr(C)大小/偏移、Rust staticlib、
  C/C++ 编译链接运行（结果25和169）、错误Rust输入的非零退出和诊断。
- 每个外部命令记录命令、退出码、stdout、stderr，结果写入 result.json。
- NaN 结果显式失败；只发布 Release 配置；其他架构及交叉执行给出配置错误。
- 当前状态：Conan/W3 真机验证通过，等待远端评审与发布。构建通过与官方制品发布分开记录。

## 知识与范围

复用 E509 的 Cargo/OpenSSL 装载问题诊断；已有知识覆盖根因，本次采用 Conan 固定依赖和进程内加载路径。
不新增 B/C 申报，不修改框架文件或 Rust/OpenSSL 配方。设备正常签名工具来自profile中的HNP SDK环境；
下载Rust程序的私有签名由包内入口执行，无需手工预签名依赖缓存。

**最终状态**：Conan/W3 真机验证通过，等待远端评审与发布。

## CI #43268 修复复验

原始发布Rust包缺少OHOS执行签名：Cargo仅chmod后仍返回Permission denied；
仅签Cargo/rustc后，rustc_driver装载失败。现在由包内入口在私有缓存中签名这三个文件，
使用文件锁及目录原子发布，并只在工具子进程设置加载路径。

最终配方revision：`b04343680b93ade1a6a41f5d8c11b194`；主机export与鸿蒙W3日志一致。
最终W3完整日志SHA256：`5186c47a4ae6931390187636f8942896e5769907a1bc79671a04233b2a5679fa`。
原始证据目录：`output/cbindgen-0.28.0/publish-20260910/repair-final/`；
同目录外的`p017.log`、`p018.log`分别记录W3与安装包附加回归。
上游161/161、消费者18/18通过；1个上游ignore文档示例仍单列。
依赖中Cargo/rustc/driver三份文件构建前后SHA256相同。
附加验证覆盖并发首次调用、默认sysroot、两种显式sysroot参数和启动器父目录名称。
附加回归不加入18个原有消费者断言的统计。

真实安装包清单校验13项；验证包SHA256：
`2a46f5c55b2a8537b243a0fe9f30b166cb195cbc0dc6f910ca2700f5c3e8e3d1`。
旧p016用于完整finish初轮，最终代码以p017的完整W3、p018产物和源码哈希为准。
远端CI、检视、提审、合入及发布状态继续按PR !9264的最新结果记录。
