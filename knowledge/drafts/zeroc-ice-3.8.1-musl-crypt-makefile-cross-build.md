# zeroc-ice-3.8.1：musl crypt 声明缺失 + 自研 Makefile 系的 conan 交叉构建交互 + vendored mcpp 第二源

## 命中场景

(1) 上游按 glibc 假定调用 `crypt_r` 的软件（PAM/密码验证路径）在 OHOS musl 上编译；
(2) 自研 GNU Make 体系（非 autotools/cmake/meson，如 Ice 的 Make.project.rules、 BIND、Sendmail 老牌 C/C++ 项目）做 conan2 交叉构建；
(3) 源码树 vendored 第三方子项目（mcpp 类）需要随主源一起获取。

## 症状（实测，zeroc-ice 3.8.1 / OHOS musl / clang 15）

1. `CryptPermissionsVerifier.cpp: use of undeclared identifier 'crypt_r'`
2. make 不传 `os=Linux` 时平台分支全走错（链接名/安装路径规则异常）
3. `tools.build:compiler_executables` conf 配了但自研 Makefile 里 `$(CC)` 仍是 gcc
4. `allTests.py` 枚举不到平台（Util.py 无 ohos 分支）
5. DataStorm `SessionI.cpp` C++17 结构化绑定 lambda 捕获编译错误（P1091）

## 根因

| 层 | 问题 |
|----|------|
| musl | crypt.h 声明面与 glibc 不同（crypt_r 无或形态不符）——上游按 glibc 隐式假定 |
| 构建体系 | 自研 Makefile 平台识别不含 ohos；**conan2 的 compiler_executables conf 不注入 buildenv 环境变量**，自研 Makefile 的 `$(CC)` 读不到——必须命令行显式 `CC=clang CXX=clang++` |
| vendored | mcpp 不在任何 registry，随主源走 conandata 第二源 |
| 测试 | 上游测试驱动的平台表无 ohos 条目 |
| C++17 | P1091（结构化绑定不能隐式 lambda 捕获）在 clang 上是硬错误 |

## 方案（实证通过，allTests.py 96/100）

- **musl crypt**：`#if defined(__linux__) && !defined(__GLIBC__)` 分支内 `extern "C"` 声明 + mutable mutex（对齐 glibc 线程语义）
- **make 交叉**：`MAKEFLAGS="os=Linux ..."` 伪装平台 + 命令行 `CC=clang CXX=clang++`；依赖路径用 `MCPP_HOME=/BZ2_HOME=/EXPAT_HOME=/LMDB_HOME=` 合并前缀变量注入
- **vendored mcpp**：conandata 增 `mcpp_source`（url+sha256），source() 解压进构建树
- **测试驱动**：Util.py 平台判定把 `sys.platform == "ohos"` 归入 Linux 分支；宿主需 `pip3 install passlib`（icehashpassword.py）
- **P1091**：结构化绑定改显式捕获

## 查重对照（knowledge/graph/index.tsv，766 条）

- `musl.*crypt` / `crypt.h` / `__GLIBC__`：**零命中**（E509 是 OpenSSL 动链，不同问题）
- 自研 Makefile：E392 覆盖 raw-makefile 三通用陷阱（BadZipFile/conf 字典/cwd）——本条是**平台伪装 + CC 命令行传播缺口 + vendored 第二源**，互补不重叠
- HMDFS 物化（ln -s→cp）：E018/E050 已覆盖，本件归入复用不申报
- 平台宏识别类（tbox E581 形态）：本条 Util.py 是**测试驱动 Python 层**识别，不同层

## 关联

- PR：!14764（zeroc-ice 3.8.1，feat/zeroc-ice-3.8.1 @51fb14a534）
- 复现：`conan create archives/z/zeroc-ice/3.8.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
