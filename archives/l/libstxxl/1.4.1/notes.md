# libstxxl 1.4.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony (aarch64)
- 状态: built

## 编译步骤

1. 下载源码：`https://downloads.sourceforge.net/project/stxxl/stxxl/1.4.1/stxxl-1.4.1.tar.gz`
2. 修改 CMakeLists.txt：将 `cmake_minimum_required(VERSION 2.6.2)` 更新为 `cmake_minimum_required(VERSION 3.5)` 以兼容 CMake 4.1.2
3. cmake 配置：`cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux -DBUILD_SHARED_LIBS=OFF ..`
4. 编译：`make -C build -j2`
5. 安装到 staging：`make -C build install DESTDIR=$TEST_PREFIX`
6. 打包：`ohc-run.py package libstxxl 1.4.1`
7. 安装到本地：`make -C build install`
8. 收尾：`ohc-run.py finish libstxxl 1.4.1 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.6.2) 导致 cmake 配置失败 | CMake 4.x 移除了对版本 < 3.5 的兼容性支持（CMP0048 等策略不再兼容） | 将 CMakeLists.txt 第18行改为 `cmake_minimum_required(VERSION 3.5)`，补丁: 0001-CMakeLists.txt.patch |
| 2 | cmake 不识别目标平台 | OpenHarmony 需要明确指定系统类型，否则 cmake 可能无法正确检测平台特性 | 添加 `-DCMAKE_SYSTEM_NAME=Linux`，使 cmake 正确识别 POSIX 系统调用（pthread、mmap、O_DIRECT 等） |
| 3 | 共享库在鸿蒙平台的兼容性风险 | 静态库更适合当前平台，避免 ELF 签名和 RPATH 问题 | 使用 `-DBUILD_SHARED_LIBS=OFF` 编译为静态库 |
| 4 | init-build 误判构建系统为 autotools | 源码根目录无 configure 脚本，但脚本默认检测为 autotools | 手动修正 .build-context 中 BUILD_SYSTEM="cmake"，以及 manifest.yaml 中 system: cmake 和顶层 build_system: cmake |
| 5 | G0 干净构建验证失败（exit 127） | clean_verify.py 对 cmake 项目仍执行 `./configure`（autotools 方式），缺少 cmake 专用逻辑 | 已知脚本限制，实际手动编译验证通过。需后续补充 clean_verify.py 对 cmake 的支持 |
| 6 | STXXL 测试默认使用只读路径 | STXXL 默认将外部存储文件写入 /var/tmp 或 /tmp，鸿蒙平台这两个目录为只读(E002) | 创建 ~/.stxxl 配置文件指定可写路径 `~/tmp/stxxl-disk/stxxl-disk.tmp` |
| 7 | 部分测试 ctest 无注册 | cmake 构建虽启用 BUILD_TESTS=ON，但未向 CTest 注册测试用例 | 手动直接执行测试程序验证 |

## 源码修改

**补丁文件**: `0001-CMakeLists.txt.patch`
- 修改位置: CMakeLists.txt 第18行
- 修改内容: `cmake_minimum_required(VERSION 2.6.2 FATAL_ERROR)` → `cmake_minimum_required(VERSION 3.5)`
- 修改行数: +2/-2
- 类型: 平台适配（CMake 版本兼容性修复）

## 依赖版本

无外部依赖。libstxxl 仅依赖：
- pthread（POSIX 线程库，系统自带）
- clang 15.0.4（C++11 编译器）
- cmake 4.1.2（构建工具）

## 验证结果

### 编译验证
```bash
# 静态库安装验证
ls ~/usr/local/lib/libstxxl.a  → 存在 (5.7MB Release 包)
ls ~/usr/local/include/stxxl/  → 存在 (algorithm, deque, io, stream 等头文件)
```

### 测试验证
```bash
# 纯内存测试（7项全部通过）
./test_binary_buffer  → exit 0
./test_cmdline        → exit 0
./test_counting_ptr   → exit 0
./test_log2           → exit 0 (2147483649→31/31/32)
./test_random         → exit 0
./test_uint_types     → exit 0
./test_tuple          → exit 0

# 外部存储算法测试（4项全部通过，需配置 ~/.stxxl）
./test_scan           → exit 0 (for_each_m 0.75s, generate 0.30s)
./test_sort           → exit 0 (50331648元素排序正确)
./test_random_shuffle → exit 0
./test_ksort          → exit 0 (OK)

# 外部存储容器测试（5项通过）
./test_queue          → exit 0 (200万操作)
./test_vector         → exit 0 (1398101元素读写)
./test_sorter         → exit 0 (25165824元素，两次验证OK)
./test_pqueue         → exit 0
./test_map            → exit 0

# 流式处理测试（3项通过）
./test_stream         → exit 0
./test_materialize    → exit 0
./test_push_sort      → exit 0

# 内存管理测试（3项通过）
./test_aligned        → exit 0
./test_block_alloc_strategy → exit 0
./test_block_manager  → exit 0
```

### 失败测试（2项，平台限制）
```bash
./test_globals  → core dump (需 /var/tmp 只读)
./test_config   → core dump (需 /tmp 只读)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libstxxl-1.4.1-ohos-aarch64.tar.gz | 5.7MB | 预编译包（Release），含 libstxxl.a + 头文件 |
| libstxxl-1.4.1-ohos-aarch64-debug.tar.gz | 456KB | 预编译包（Debug） |

## 注意事项

1. **cmake_minimum_required 版本**：任何使用 CMake 4.x 的平台都需要 ≥ 3.5，这是 CMake 策略兼容性要求
2. **磁盘配置**：运行 libstxxl 程序需要在 `~/.stxxl` 中配置可写磁盘路径，否则默认尝试 /var/tmp（只读）
3. **静态库模式**：建议使用静态库（BUILD_SHARED_LIBS=OFF），避免鸿蒙平台共享库的签名和兼容性问题
4. **C++11 要求**：libstxxl 需要 C++11 编译器支持（已确认 clang 15 支持）
5. **O_DIRECT**：部分 I/O 实现使用 O_DIRECT，在鸿蒙平台可能需要回退到非直写模式

---

**编译结束**: 2026-06-10 03:35
**最终状态**: built