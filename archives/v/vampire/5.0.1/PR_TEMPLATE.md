## 编译信息

- **软件**: vampire 5.0.1
- **构建系统**: CMake
- **编译日期**: 2026-06-29
- **许可证**: BSD-3-Clause
- **主页**: https://github.com/vprover/vampire

## 软件描述

Vampire 是一款高性能一阶逻辑定理证明器，由英国曼彻顿大学开发。支持 TPTP 和 SMT-LIB 2 输入格式，内嵌 CaDiCaL 2.1.3 SAT 求解器。

## 编译方式

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF
make -j1
make install DESTDIR=$TEST_PREFIX
```

- 构建系统: CMake (Release, BUILD_SHARED_LIBS=OFF)
- 编译器: Clang 15.0.4
- 无外部依赖（内嵌 CaDiCaL 2.1.3、Minisat）
- make -j1 编译约 200 个 C++ 源文件，耗时约 944 秒

## 制品文件

- `vampire-5.0.1-ohos-aarch64.tar.gz` (~24MB)
- 二进制: ELF 64-bit LSB arm64, static, not stripped

## 测试验证

- `vampire --version` → Vampire 5.0.1 + CaDiCaL 2.1.3 ✅
- 定理证明: `![X]:(p(X) => p(X))` → SZS Theorem, 0.001s ✅
- 定理证明: 苏格拉底三段论 → SZS Theorem, 0.002s ✅
- Conan 8 道门禁全部 PASS ✅

## 禁用功能

- Z3 SMT 支持（可选，缺失时自动跳过）

## 提交文件

- `archives/v/vampire/manifest.yaml`
- `archives/v/vampire/README.md`
- `archives/v/vampire/commands.json`
- `archives/v/vampire/5.0.1/conanfile.py`
- `archives/v/vampire/5.0.1/conandata.yml`
- `archives/v/vampire/5.0.1/test_package/` (含 MANIFEST.yml)
- `archives/v/vampire/5.0.1/manifest.yaml`
- `archives/v/vampire/5.0.1/notes.md`
- `archives/v/vampire/5.0.1/reports/`

## 参考

- 上游: https://github.com/vprover/vampire/releases/tag/v5.0.1

---

Co-authored-by: OpenDesk <opendesk@openharmony.cn>
