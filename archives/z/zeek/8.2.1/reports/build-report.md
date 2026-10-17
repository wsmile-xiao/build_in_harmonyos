# zeek 8.2.1 编译过程记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名称 | zeek |
| 版本 | 8.2.1 |
| 编译日期 | 2026-09-21（主构建）/ 2026-09-22（W3 复验与打包） |
| 编译者 | AtomCode (qwen3.8) 适配流程（模式 B 探索编译 + Conan 配方固化） |

## 环境信息

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS PC（HongMeng Kernel） |
| 架构 | aarch64 |
| 编译器 | clang/clang++ 15.0.4（musl + libc++ 15.0.4，C++17） |
| 构建系统 | CMake 4.1.2 + Conan 2.29.1（OHOS 适配版） |

## 编译过程

### 1. 源码获取

```bash
# 官方 tag 源码（conandata.yml 声明，sha256 已核验）
wget https://download.zeek.org/zeek-8.2.1.tar.gz
tar -xzf zeek-8.2.1.tar.gz
# 子模块合并：auxil/spicy（HILTI）、auxil/broker、3rdparty 并入源码树
# tarball 含目录别名符号链接环 → cp -a 保留符号链接（HMDFS 拒绝硬链接）
```

### 2. 配置

```bash
# Conan 交叉构建（CI 同源 profile）
conan create archives/z/zeek/8.2.1 -pr:a ci/conan/profiles/ohos-aarch64 --build=missing

# 配方内 CMake 关键选项（最小可行 core 构建）
-DDISABLE_SPICY=ON -DDISABLE_JAVASCRIPT=ON
-DENABLE_CLUSTER_BACKEND_ZEROMQ=OFF
-DINSTALL_ZEEKCTL=OFF -DINSTALL_ZKG=OFF -DINSTALL_ZEEK_CLIENT=OFF
# toolchain 注入：CMAKE_SYSTEM_NAME=Linux（OHOS 为 Linux 内核 + musl，语义等价）
```

**配置输出关键信息**：
```
fiber: aarch64 分支命中（toolchain 注入 CMAKE_SYSTEM_NAME=Linux 后）
libkqueue: src/linux/* epoll 分支命中
OHOS libc++ 15.0.4: <memory_resource>/ranges 缺口 → shim -I 注入
```

### 3. 编译

- 驱动方式：conan create 内部驱动 CMake 构建（make 等效），无手工 make。
- **编译耗时**：全量约 40 分钟（W3 conan create 日志 10555 行）。
- **编译警告/错误**：探索阶段共定位 10 个平台/适配点，全部修复并留档（P1-P10，notes.md「平台点实测三件套」逐项 现象/证据/修复）：
  - P1 CMake 平台探测落空（fiber/libkqueue 的 OS 白名单不含 OHOS）
  - P2 host 生成器 ALIAS 未展开（bifcl/binpac/gen-zam，CMake 4.1.2，Error 127）
  - P3 libc++ 缺 C++20 ranges 算法（47 文件 83+ 处）
  - P4 libc++ 缺 `<memory_resource>`（broker 13 项单测曾 SEGFAULT）
  - P5 musl 缺 pthread 线程取消符号（链接期 undefined reference）
  - P6 缺 fts.h（zeekygen）
  - P7 sockaddr_storage 双定义（UAPI 头栈冲突）
  - P8 旧 libc++ construct_at 聚合体初始化（CallInfo/DispatchInfo）
  - P9 机械改写引入的转换 bug：broker C 数组被当容器 `.begin()`（3 处，改 std::begin/std::end）
  - P10 broker.backend 测试受 HMDFS /tmp 只读影响（平台限制 E002，非代码缺陷，见 test-report.md）

### 4. 安装

- conan create 自动 stage 入 conan 包（111MB）；本地打包用 PackageBuilder 工具
  生成 CI 等价制品 `packaging/zeek-8.2.1-ohos-aarch64.tar.gz`（约 138MB，
  8 顶层目录齐全，.packaged 标记）。

**安装文件列表（包树实测）**：
```
bin/            zeek, zeek-cut, btest, bifcl, binpac 等命令行工具
lib/            libbroker.so（含 .4/.2.8 版本链接）、libbinpac.so、libparaglob.a、Broker/cmake
include/zeek/   头文件
share/          脚本与数据文件
etc/ logs/ spool/ var/   运行时目录
```

## 遇到的问题

P1-P10 详见 notes.md「平台点实测三件套」；全部修复已固化为 76 个 patches
+ 2 个 shims（shims 走 -I 注入 / weak 符号链入，不进 patches）。
R8 合规：无 `__OHOS__` 平台宏进 patches。

## 验证测试

```bash
zeek --version                    # → zeek version 8.2.1 (exit 0)
ctest -R "broker.*"               # 26/26 通过（100%；broker.backend 经 TMPDIR 补丁+可写 TMPDIR 运行解决）
conan create ...                  # W3 本地 CI 全绿（.ci-result.json exit_code=0）
test_package (conan L1)           # 1/1 通过
```

## 总结

Zeek 8.2.1 在 OHOS aarch64 上的适配难点集中在三类：
① CMake 平台探测白名单（OHOS 落空）→ toolchain 注入 Linux 语义；
② OHOS musl/libc++ 符号缺口（pthread 取消、pmr、ranges、fts）→ weak shim + 可移植改写，
   全部 R8 合规（无平台宏）；
③ 交叉编译私有 host 工具链（bifcl/binpac/gen-zam）→ CMake 4.x ALIAS 展开缺陷
   用 `$<TARGET_FILE:...>` 修复。

最终 76 补丁 + 2 shims 达成：core 引擎/工具链/broker 全量编译链接运行通过，
单元测试 26/26（100%，见 test-report.md）。
