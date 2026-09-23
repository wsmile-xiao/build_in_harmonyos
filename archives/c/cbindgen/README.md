# cbindgen

cbindgen 从 Rust 公共 C ABI 生成 C、C++ 和 Cython 声明，适合 Cargo crate/workspace 与单个 .rs 文件。
Conan 中用 tool_requires("cbindgen/0.28.0") 引入，并启用 VirtualBuildEnv；运行 cbindgen --lang C --output ffi.h path/to/crate。

本包面向原生 OHOS aarch64 Release 构建；Rust 工具链以独立依赖提供。Cargo 的 OpenSSL 库仅在
Cargo 子进程中加载。交付 bin/cbindgen 是真实 Rust 程序，文档位于 share/cbindgen。
上游：https://github.com/mozilla/cbindgen。版本验证和限制详见 0.28.0/notes.md。
