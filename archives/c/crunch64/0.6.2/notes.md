# crunch64 0.6.2 HarmonyOS PC 适配笔记

## 方案与范围

交付原生 OHOS armv8 的 C API 静态库 `libcrunch64.a`、完整 C 头文件及 MIT 许可。
核心保持上游 Rust 实现，使用 `std,c_bindings` 特性和上游 Cargo.lock。
通过已发布的 `rust-toolchain/1.97.1` 与 `openssl/3.5.6.1.1` 工具依赖在干净 CI 中构建。
Rust 工具与其动态库仅在构建私有目录中签名；OpenSSL 私有动态库仅用于 Cargo 运行。
不发布 CLI 或 Python 扩展，消费者不依赖 Rust 工具链、OpenSSL、Python 或 deviceinfo。
构建时将 Conan 当前的原生 Python 解释器及其共享库复制到构建私有目录并签名，
使用该运行时生成和执行仅用于测试的 PyO3 扩展。

## 环境预检

- Windows 控制端；SSH 构建端为 HarmonyOS、HongMeng Kernel 1.12.0、aarch64。
- 设备 API 实测 `OpenHarmony-6.1.0.115`、API 23；profile 的 `os.version=6.0` 仅为构建配置，未在6.0运行系统上复验。
- Python 3.12.9、OHOS Conan 2.29.1、Clang 15.0.4、CMake 4.1.2。
- `conan download --only-recipe` 验证两个工具依赖已发布；原生 profile 的二进制获取成功，未从源码构建依赖。
- `lang-preflight --lang rust` 通过。已有 rust-toolchain 包满足根 SKILL.md W0b 的工具链例外。
- 本次实际参考：`archives/l/libimagequant/4.4.1/notes.md`、该版配方、`archives/c/cbindgen/0.28.0/`。
- 用户提及的 `tests/SKILL.md` 当前不存在；采用根 `SKILL.md` 和 `tests/` 中的框架检查规范。

## 上游测试清点

官方 tag `0.6.2`，提交 `35bb166ae26ee5143af7a62844aa084d4ecf33ce`。
源码 tarball SHA256：`073c179a66d03ba176e661b2c327f708807b37005df42a65986f87005314611d`。

| 类型 | 数量 | 清点依据 |
|---|---:|---|
| Rust 单元测试 | 161 | `lib/src/{yaz0,yay0,mio0,gzip}.rs` 中 15 个 rstest 函数按 test_data 展开：44+44+40+33 |
| C 绑定集成比较 | 97 | 原始 `c_bindings/tests.c`，32 个 N64 fixture 各压缩/解压一次，加 33 个 gzip fixture |
| Python 绑定比较 | 97 | `python_bindings/tests.py` 对相同 fixture 集合进行比较；需单独构建 PyO3 扩展 |
| CLI 单元测试 | 0 | CLI 无测试函数；workspace 的 CLI 测试目标仍编译和执行 |

Conan 构建强制执行全部161个 Rust 用例、97次 C 比较及97次 Python 比较，上游共355项。
加上6项消费者测试，合计361项。未修改任何上游测试源码、Python包装层或 fixture。

Python 测试用独立 `python-target` 构建目录启用 `python_bindings`，复制原样包装层，签名扩展，
使用当前解释器的私有副本执行原样 `python_bindings/tests.py`。启动前验证版本与扩展的实际导入路径，
禁用用户 site 和 Python 优化模式，确保没有误用已安装包或省略来源断言。
测试扩展不打包，也不影响 `target/release/libcrunch64.a` 的 C 交付构建。

首次扩展加载提示 `_Py_IncRef` 缺失；检查确认该符号由本机 libpython 导出，
显式链接 `sysconfig` 提供的 libpython 路径及运行时搜索路径后97项通过。
Conan 的 `EnvVars.apply()` 会将 unset 转成空字符串，PyO3 却把空 `PYO3_CONFIG_FILE` 当路径；
配方在可恢复的环境上下文中真正移除这些变量，结束时恢复原环境。

PR #9964 的远程构建 #46960 使用 `/data/service/hnp/bin/python3`，在加载 Conan 用户缓存中的
测试扩展时返回 `Permission denied`，与知识库 E212 的 HNP Python 加载权限限制一致。
配方现将同一解释器和同版本 libpython 复制、签名至 `python-runtime`，保留原 `PYTHONHOME`
读取标准库，通过私有 `LD_LIBRARY_PATH` 和链接路径加载私有共享库。运行前核验解释器、
扩展路径与 `/proc/self/maps` 中的 libpython；HMDFS 物理路径前缀不同，使用包含 Conan
唯一构建目录的六段路径后缀验证。测试仍为强制执行，不修改全局安装、系统权限或上游测试。
此修复已通过本机完整 Conan/W3；本机原解释器位于用户目录，远程 HNP Worker 仍需重跑确认。

后续构建 #46989 换到 Worker 012，由 `/data/app/bin/python3` 启动，Rust/C 测试通过后，
因 `sysconfig.LIBDIR` 保留了不存在的原编译前缀而在 Python 准备阶段失败。
参考 `archives/r/ruamel-yaml-clib/0.2.15/conanfile.py` 和
`archives/e/eigenpy/3.13.0/conanfile.py` 中的安装重定位处理，现按当前解释器的运行前缀、
真实可执行文件所在前缀及 `base/platbase` 查找 `lib/lib64`，最后兼容 `LIBDIR/LIBPL`。
仅匹配当前 Python 配置给出的库文件名，优先接受带版本的 `INSTSONAME`，无需开发软链接；
私有解释器启动后额外核验完整 `sys.version`，并输出原配置与实际选中的库路径供 CI 诊断。
五项路径回归覆盖失效编译前缀、安装目录迁移、lib64、仅版本库文件及拒绝错误 Python 版本；
旧配方在其中四个有效安装场景报错，修复后五项通过。回归脚本和原始结果保存在本地报告目录，
这些配方专项检查不计入上游355项测试数量。
随后在完整 `conan create` 进程内注入不存在的 `LIBDIR`，355项上游测试和6项消费者测试
全部通过；恢复正常环境后的 Conan G1/G2 和 W3 也退出0。中间一次因测试副本残留镜像列表
造成嵌套代理的下载已中止并保留日志，恢复提交中的官方源码配置后完成最终复验。

## 新增测试与首轮结果

`test_package` 实质链接已安装的 Conan 库与头文件，六个 CTest 测试：
三种 N64 格式分别做 1/4/31/32/33/4096/4097 字节往返；错误返回及大小溢出；
gzip 六个压缩等级×两种内存模式的独立 CRC32/长度尾部向量；鸿蒙设备信息与文件映射往返。

鸿蒙专用测试调用 `OH_GetOSFullName`、`OH_GetSdkApiVersion` 取得实际平台数据，跨 Rust/C ABI
压缩，再解压至用户可写目录的共享文件映射；`msync` 后重新映射逐字节核对，最后清理临时文件。

首轮 `conan create`：核心库、161 个 Rust 用例、97 次 C 比较通过；鸿蒙测试通过。
新增小输入测试暴露 Yay0/MIO0 的缓冲区上界缺陷：n=1 时 `compress_bound=18`，实际需要21，
压缩返回 `OutOfBounds`。`SIZE_MAX` 上界请求也发生算术回绕。修复前三个相关回归测试均失败。

## 源码修改清单

修改仅涉及 `lib/src/yay0.rs` 和 `lib/src/mio0.rs`。`size_for_compressed_buffer` 修正为：
控制位按 32 位字保存，正确最坏上界为 `n + 4*ceil(n/32) + 16`；用 checked_add 检查溢出并返回
既有 `OutOfBounds` 错误。压缩算法、文件格式、C ABI、原有 fixture 和测试保持不变。
补丁由仓库 `ohc-run.py refresh-patch --auto` 生成并 dry-run 验证，不手写补丁。
另移除两处把已经是 `usize` 的移位结果再次转为 `usize` 的冗余转换，使原样上游
`cargo clippy --all --all-targets --all-features -- -D warnings` 在当前工具链下通过；无行为变化。

已额外执行上游 `cargo fmt --all -- --check`、上述 Clippy 命令及
`python3 -m mypy --show-column-numbers --hide-error-context .`，均退出0；mypy检查7个源码文件。
源码未定义 Rust 文档测试，所用 OHOS 工具链也未提供 rustdoc。其他操作系统、Python版本、
Rust 1.74 MSRV 和发行 wheel 矩阵不属于这台原生 PC 的可用环境，不声称完成这些矩阵验证。

## 验证状态

包含Python的最终配方通过 Conan G1/G2 干净构建及 W3 完整本地 CI：上游355/355、
消费者6/6全部通过，零失败、零跳过；L1e反向依赖验证通过。独立源码审查无未解决问题。
对照原始源码核验90个上游测试、包装层及fixture文件和4个Rust测试模块未改变；
ELF符号及包内容检查确认交付C静态库没有Python未定义符号，也不包含Python文件或共享库。

两份补丁、配方和测试的审查哈希，以及实际 W3/CTest 日志保存在本地 `reports/test-report.md`；
报告及运行标记按仓库规则不纳入 Git 提交。
最终 W3 日志 SHA256：`e385b0acc1ff713212fccb1f86df95f25ce934c719e6b4333d2d8114a9d84a49`。

旧 clean-verify 仅支持 configure/make，Cargo 无 configure，故该旧关卡不能标为通过；
实际干净构建由 Conan G2 与 W3 完成。完整 finish 另有仓库既存知识草稿和旧打包布局提示，
具体限制保留在报告，未修改公共 CI 或伪造通过标记。仅验证 armv8 Release。

代码位于从 upstream/main `5dff0c6a5c137331eb45d77ba4c2326dc01a0f4e` 创建的
`feat/crunch64-0.6.2` 分支。提交范围仅为 crunch64 归档；原有本地文件126个均经 SHA256 核对未改变。
---

**编译结束**: 2026-09-14 17:34
**最终状态**: built
