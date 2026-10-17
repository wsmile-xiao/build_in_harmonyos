# dumb 2.0.3 适配笔记

## 软件信息
- 软件：dumb 2.0.3（上游 kode54/dumb tag 2.0.3，Zlib OR FreeType 双许可——申报 Zlib）
- 定位：DUMB (Dynamic Universal Music Bibliotheque) tracker 音乐模块库——纯 C 解码/渲染 IT/XM/S3M/MOD 及十余种模块格式 + 重采样/LPC 助手 + dumbfile I/O 抽象
- 构建系统：上游 CMakeLists（add_library dumb 共享库）
- 分支 feat/dumb-2.0.3；worktree ~/huawei/worktrees/j669539/dumb-2.0.3

## W0/W0b
- W0 preflight：PASS（零外部依赖——纯 C + libm；examples 的 argtable2/SDL2 已关）
- W0b：本仓库无 dumb 历史归档；CMake 库先例参照 vorbis/ogg 系列
- lang-preflight：c 判定（src/ 全纯 C；examples/ 为 C 演示不参与构建）

## 源码检查（上游 2.0.3 tarball，SHA256 99bfac926aeb8d476562303312d9f47fd05b43803050cd889b44da34a9b2a4f9）
- src/core+helpers+it：库本体（纯 C）
- src/allegro/：Allegro4 绑定（BUILD_ALLEGRO4=OFF 跳过——Allegro 未适配）
- examples/dumbout.c+dumbplay.c：演示程序（argtable2+SDL2 音频依赖，非测试）
- 无注册测试（全树 grep add_test/enable_testing = 0 命中；无 tests/ 目录；无 CI 工作流）
- 无需源码补丁 → patches 为空

## 关键适配点（实测记录）
1. **CMake 4.x 兼容**：上游 cmake_minimum_required(3.1) 被 CMake 4.1 拒绝——`CMAKE_POLICY_VERSION_MINIMUM=3.5` shim 必须**环境变量**传递（toolchain/generate() 内 set 在 project() 才生效，而 minimum_required 在其前已失败）；用 conan Environment().define + vars().apply() 上下文注入
2. **三开关**：BUILD_EXAMPLES=OFF（argtable2+SDL2 音频）、BUILD_ALLEGRO4=OFF、USE_SSE=OFF（aarch64 上游 check_c_compiler_flag 也会自跳过，显式关闭）
3. **duh_render_int 契约**（test_package 踩坑）：sig_samples 须传 `sample_t **sigptr = NULL` + `&sigptr`——库内分配复用；误传栈数组 → destroy_sample_buffer 对栈指针 free → SEGV 139。ASan 设备实跑定位（dumb-asan 目录证据）
4. 产物：libdumb.so（shared 默认——非系统同名库，Conan 管理依赖链 R26 合规）

## 上游测试统计与执行（rule4 口径）
- 上游注册测试：**N=0**（无 tests/ 无 add_test 无 CI——如实申报；examples 2 个演示程序非测试：dumbout 需 argtable2、dumbplay 需活音频设备）
- 上游验证形态=库构建本身：本地 conan create 全绿即等价覆盖

## 适配后测试（消费者，test_package）
- test_dumb.c 12 项断言全过（failures=0，ASan 全链复验无内存错误）：
  - dumb_load_any 拒绝缺失文件（错误路径）
  - S3M 真解析器：dumbfile_open_memory + dumb_read_s3m 解析最小 S3M（字段级 fixture：type 0x1A/0x10 标记/n_orders=1/SCRM@0x2C）
  - duh_get_length > 0 / duh_start_sigrenderer / duh_render_int 渲染 1024 立体声样本（IT 渲染核心：重采样+混音）
  - MOD 真解析器：dumb_read_mod 解析最小 MOD（M.K.@1080 + 1024B pattern）+ 同套渲染链
  - 库常量健全性
- 渲染为静音属预期（fixture 无乐器）——验证的是解析器/渲染器管线无崩溃且产出有限样本

## OHOS 平台要点
- 纯 C + libm，无平台 API；headless 全可测（渲染走内存缓冲无音频设备依赖）
- 测试二进制运行需 E077 签名
- CMAKE_POLICY_VERSION_MINIMUM shim 见 knowledge_gained（可复用：所有 minimum_required<3.5 的上游）

## 验证记录
- conan create（G2）+ test_package 全链路本地通过（12/12 断言 + ASan 复验）
- status：built（上传发布须等合并后 release 流水线）
