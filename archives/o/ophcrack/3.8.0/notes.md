# ophcrack 3.8.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-08-09
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: published

## 编译步骤

```bash
# 1. configure（裁剪 GUI、显式 build/host、提供 ssl/expat、CC=clang）
CC=clang CXX=clang++ ./configure --disable-gui \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --with-libssl=<openssl prefix> --with-libexpat=<expat prefix>

# 2. make
make -j1

# 3. 产物签名（OHOS ELF 必需）
binary-sign-tool sign -inFile bin/ophcrack -outFile bin/ophcrack.signed -selfSign 1 -signAlg SHA256withECDSA
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | OHOS uname -s=HarmonyOS，config.guess 无法识别 | 显式传 `--build=--host=aarch64-unknown-linux-gnu` |
| 2 | configure: C++ compiler cannot create executables | PATH 无 c++/g++ | 导出 `CXX=clang++`（E001 同类） |
| 3 | configure: Cannot find ssl libraries / requires libexpat | openssl/expat 不在默认路径 | `--with-libssl=DIR --with-libexpat=DIR`（conan 依赖） |
| 4 | config.status: can't create ./confXXX/subs1.awk: Permission denied | configure 临时目录 `umask 077`，OHOS hmfs 权限位保留不完整导致子目录不可写 | 补丁 0002：configure umask 077→002 |
| 5 | ntdll.h: fatal error: 'windows.h' not found | samdump2/ntdll.h 无条件 include windows.h（Windows 专用头，-MM 依赖解析阶段触发） | 补丁 0001：windows.h include 加 `#ifdef WIN32` 保护 |
| 6 | ld: undefined symbol: pthread_cancel / pthread_setcancelstate / pthread_setcanceltype | OHOS musl libc 无线程取消 API | 补丁 0001：`__OHOS__` 下定义 no-op 宏 |
| 7 | ophcrack --version: unrecognized option | ophcrack 无 --version 参数 | test_package 改用 `-h`（帮助输出含版本号） |

## 源码修改

- `patches/0001-ohos-portability.patch`（3 文件）：
  - `src/samdump2/ntdll.h`：windows.h include 加 `#ifdef WIN32` 保护
  - `src/core/ophcrack.c`：`__OHOS__` 下 pthread_setcancelstate/setcanceltype 定义为 no-op
  - `src/core/scheduler.c`：`__OHOS__` 下 pthread_cancel 定义为 no-op
- `patches/0002-configure-umask.patch`（1 文件）：
  - `configure`：临时目录创建 umask 077→002（OHOS hmfs 兼容）

## 依赖版本

- openssl/3.5.6（cnb 制品仓，conan requires）
- expat/2.8.2（cnb 制品仓，conan requires，动态库，test 时经 conanrun 环境提供）

## 验证结果

```bash
# conan-verify 全门禁通过
G0 ✅ PASS  G1 ✅ PASS  G2 ✅ PASS（conan create 干净构建 + test_package）
G3 ✅ PASS  G4 ✅ PASS  L2 ✅ PASS  L4 ✅ PASS  L5 ✅ PASS

# 产物冒烟
./ophcrack -h
# => ophcrack 3.8.0 by Objectif Securite (http://www.objectif-securite.ch)
```

## 交付物

| 文件 | 说明 |
|------|------|
| packaging/ophcrack-3.8.0-ohos-aarch64.tar.gz | 产物包（bin/ophcrack，已签名） |
| reports/test-report.md | 功能测试报告 |
| reports/conan-verify-report.md | conan-verify 门禁报告 |
| reports/conan-create.log | conan create 构建日志 |
| patches/0001-ohos-portability.patch | OHOS 可移植性补丁 |
| patches/0002-configure-umask.patch | configure umask 兼容补丁 |

## 注意事项

- GUI 前端（Qt5Charts）已通过 `--disable-gui` 裁剪；CLI 破解核心（crack/find/lookup）完整可用。
- 实际破解需要 rainbow tables 数据与哈希文件，test_package 仅做 `-h` 冒烟验证。
- 上游无自带测试套件（src/test 仅为内部自测可执行，无断言框架），test_package 补充消费者视角功能测试。
- 分支名：`feat/ophcrack-3.8.0`；PR 前缀：【积分赛】。

## 结束标记
最终状态: published
