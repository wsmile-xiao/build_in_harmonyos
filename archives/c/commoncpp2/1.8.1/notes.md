# commoncpp2 1.8.1 适配笔记

## 编译环境
- **构建系统**: autotools (configure + make)
- **编译日期**: 2026-08-27
- **编译器**: clang 15（OHOS 6.0 交叉工具链）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（配方内联处理——无独立补丁文件）

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/commoncpp2/1.8.1 --build=missing
```

### 1. 源码获取（source()）
沙箱下 `get()` 抛 PermissionError——改用 `download()` + 手动解压：
```bash
tar -xzf commoncpp2-1.8.1.tar.gz --no-same-owner || true
cp -a commoncpp2-1.8.1/. . && rm -rf commoncpp2-1.8.1
```

### 2. 配置（configure）
- **旧版 config.guess/config.sub（2007 年）不识别 ohos**：config.guess 插
  `*-linux-ohos*) echo ${UNAME_MACHINE}-unknown-linux-ohos ; exit 0 ;;` 分支；
  config.sub 把 `linux-gnu*` 替换为 `linux-gnu* | linux-ohos*`
- **C++98 老代码**：CXXFLAGS 加 `-std=c++98 -fpermissive -Wno-error
  -Wno-deprecated-declarations`（-include pthread_stub.h 注入 stub）
- **依赖路径**：CFLAGS/CXXFLAGS 加 `-I<dep>/include`、LDFLAGS 加 `-L<dep>/lib`
  （zlib/openssl）

### 3. config.status mktemp（关键攻坚，同 dpkg）
`/tmp` 只读 + `$HOME/.ci_logs` 不可写 + autoconf 相对路径 mktemp →
`./confXXXXXX/subs1.awk: Permission denied`。解法：
- `TMPDIR=/data/storage/el2/base/cache`（可写）
- configure/config.status 的 `mktemp -d "./confXXXXXX"` 模板改为
  `mktemp -d "${TMPDIR}/confXXXXXX"`（带引号完整串——无引号/不完整不命中）
- 详见 SKILL: `docs/skills/autotools-config-status-mktemp-sandbox.md`

### 4. 源码 patch（鸿蒙 libc 差异）
- **pthread_stub.h**：`pthread_testcancel` 空实现 + SO_ORIGINAL_DST +
  S_IREAD/S_IWRITE 别名 + mkfifo 声明（`-include` 注入）
- **inc/cc++/string.h**：friend 声明默认参数（现代 clang 报错）——
  去掉 `char delim = '\n', size_t size = 0` 默认参数 + 调用处补回参数
- **src/friends.cpp**：`ts.tv_usec` → `ts.tv_nsec`（鸿蒙 timespec 无 tv_usec）
- **src/nat.cpp**：注释 netfilter include（鸿蒙 sysroot 头链触发
  sockaddr_storage 重定义——netfilter 功能非必需）

### 5. 编译（make -j4）
```bash
make -j4
```

### 6. 上游测试（build() 集成——rule 4 实测回填）
tests/ 目录（bug1/bug2/thread1/digest/tcpstr1/url1——test.sh 对比 output.txt）：
build() 内编译并运行，实测 **5/6 通过**（bug1/bug2/digest/tcpstr1/url1 OK）：
```bash
clang++ -std=c++98 -fpermissive -I<src>/inc -include pthread_stub.h \
  <src>/tests/<t>.cpp <src>/src/.libs/libccext2.a \
  <src>/src/.libs/libccgnu2.a -L<zlib>/lib -lz -lpthread -o test_<t>
timeout 10 ./test_<t>   # 超时即 FAIL（如实记录）
```

**thread1 状态（修复 + 实测）**：
- **修复 Thread::sleep 换算 bug**：friends.cpp 的 `ts.tv_usec = (timeout % 1000) * 1000000`
  原 patch 改为 `ts.tv_nsec = (timeout % 1000) * 1000000000`（×10⁹ 溢出 tv_nsec
  合法范围 [0, 10⁹)，nanosleep 立即 EINVAL 返回 → sleep 变 0ms → thread1 的
  WaitNValue 轮询瞬间耗尽而 ko）——已修正为 `× 1000000`（1ms = 10⁶ ns），
  sleep 实测恢复 10ms 正常休眠
- **修复后实测**：thread1 **前 4 个检查点全过**（`set n to 1...ok`、
  `thread is working` 两处 `ok`），随后卡在 `Testing suspend & resume` 段
  （suspend() 用 pthread_kill(SIGWINCH) 挂起线程 + sigwait 等待恢复——
  OHOS 沙箱信号投递/处理不稳定，多次运行卡点不一致）——**环境限制，
  非配方可修 bug**——整体仍记 FAIL（timeout 10），通过率 5/6 如实记录

### 7. 打包（package()）
```bash
make install DESTDIR=<package_folder>
```
in-source 构建——手动执行 make install（Autotools.install() 默认在
build_folder 无 Makefile 会失败——同 dpkg 修复）。

## 验证结果
- **构建**: `commoncpp2/1.8.1: Package created`
- **上游测试**: 实测 **5/6 通过**（bug1/bug2/digest/tcpstr1/url1 OK；thread1
  前 4 检查点通过后卡在 suspend 段——OHOS 沙箱信号机制环境限制——如实记录，
  rule 4）
- **R34 消费者验证**: test_package — 头文件 + lib + smoke C++ 链接/运行 OK
- **修复沉淀**: Thread::sleep 的 tv_nsec 换算 bug（×10⁹ 溢出 → ×10⁶ 正确）——
  autotools 库 sleep 类问题的通用排查点

## 已知限制
- 取消点检测（pthread_testcancel）为 stub 空实现（鸿蒙 libc 无此函数）
- netfilter 相关功能（nat.cpp）已禁用（头链兼容性问题）
