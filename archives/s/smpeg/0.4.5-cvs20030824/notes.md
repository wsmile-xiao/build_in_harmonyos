# smpeg 0.4.5-cvs20030824 适配笔记

## 编译环境
- 构建系统: autotools + libtool（tarball 自带生成好的 `configure`，无需 autoreconf）
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）、clang++（`-stdlib=libc++`，严格 `-std=c++17`）
- 状态: built

## 版本说明
- 上游: https://www.libsdl.org/projects/smpeg/ （SDL MPEG 播放库），版本 `0.4.5-cvs20030824`（2003 年 CVS 快照）
- 源码: `https://deb.debian.org/debian/pool/main/s/smpeg/smpeg_0.4.5+cvs20030824.orig.tar.gz`，
  sha256 `1276ea797dd9fde8a12dd3f33f180153922544c28ca9fc7b477c018876be1916`
- 版本号沿用赛事清单（首次适配，R37）

## 编译步骤
```bash
conan create archives/s/smpeg/0.4.5-cvs20030824 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess`（2001-01-17）报 `cannot guess build type` | 老 config.guess 不认识 HarmonyOS；且探测程序在沙箱内不可执行（E007） | 显式 `--build/--host=aarch64-linux-ohos` + 补丁 0003 让 config.sub 认识 aarch64/ohos（与 `aalib/1.4p5` 同一三行补丁） |
| 2 | `configure: error: cannot run C compiled programs`（`Error loading shared library libatopology.so`） | conftest 链接 SDL → alsa，运行期找不到 alsa 的共享库 | `generate()` 把依赖的 `libdirs` 注入 `LD_LIBRARY_PATH`（configure 阶段生效） |
| 3 | `configure` 报 `sdl-config: can't execute: Permission denied` | 制品仓 `sdl/1.2.15` 不含 `sdl-config` 脚本，`AM_PATH_SDL` 必须执行它 | 在构建目录生成等价 `sdl-config` 外壳；**必须显式设置可执行位**（HMDFS 新建文件默认 0640，Conan 的 chmod 未落位，改用 `os.chmod(mode | S_IXUSR…)`，同 `sdl_mixer` / `lbreakout2` 先例） |
| 4 | `config.status` 报 `./confstatXXXXXX/out: Permission denied` | HMDFS 给新目录加 setgid，`umask 077` 建的 config.status 临时目录不可用（E129/E011） | 补丁 0004：configure 内两处 `umask 077` → `022` |
| 5 | 编译报 `ISO C++17 does not allow 'register' storage class specifier` | 2003 年代码大量使用 `register`（13 文件 87 处），C++17 已移除该存储类 | 补丁 0001：删除 `register` 关键字（语义不变） |
| 6 | `huffmantable.cpp` 报 `constant expression evaluates to -1 which cannot be narrowed to type 'unsigned int'` | 表格初始化用 `0-1` 作为无符号字段的 -1 哨兵，C++11 起列表初始化禁止窄化 | 补丁 0001：`0-1` → `(unsigned int)(0-1)` |
| 7 | `MPEGaudio.cpp` 报 `use of undeclared identifier 'Play_MPEGaudioSDL' / 'Decode_MPEGaudio'` | 这两个函数只在类内以 `friend` 声明；现代编译器不再把 friend 声明引入外层命名空间 | 补丁 0001：在 `MPEGaudio.h` 补命名空间级声明（`THREADED_AUDIO` 下含 `Decode_MPEGaudio`） |
| 8 | `libsmpeg.la` 链接阶段 `ar: /audio/.libs/libaudio.a: No such file or directory`（libtool 从空的 dir 变量拼路径） | HMDFS 下 libtool 的 `cd $dir && pwd` 取不到当前目录（E114/E386），相对路径前缀变空 | `build()` 预置 `os.environ["PWD"] = self.build_folder`（仓库内多例同款兜底） |
| 9 | `plaympeg` 链接报 `undefined symbol: operator new[]` | `plaympeg.c` 是 C 源文件，用 C 驱动链接静态 C++ 库；上游正是靠 `libsmpeg_la_LDFLAGS` 里的 `-lstdc++` 补 C++ 运行时 | 补丁 0002：`-lstdc++` → `-lc++`（OHOS 只有 libc++，不删该标志） |
| 10 | 上游无测试套件 | 2003 年快照没有 tests 目录、没有 check 目标 | `build()` 内置 grep/find 审计留证（R51 N=0）+ 6 条消费者断言（`test_package/test_smpeg.c`） |

## 源码修改
- `patches/0001-cxx17-source-modernisation.patch` — `register` 删除（87 处/13 文件）、列表初始化窄化显式转型（6 处）、friend 声明的命名空间级声明
- `patches/0002-libtool-cxx-link-driver.patch` — `-lstdc++` → `-lc++`
- `patches/0003-config-sub-aarch64-ohos.patch` — config.sub 认识 aarch64 与 ohos
- `patches/0004-configure-config-status-umask.patch` — config.status 临时目录 `umask 077` → `022`

## 依赖版本
- `sdl/1.2.15`（制品仓已发布，静态库；其 alsa 后端在运行期需要 `libasound.so`/`libatopology.so` 可被加载）

## 验证结果
```bash
conan create archives/s/smpeg/0.4.5-cvs20030824 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0；交付 lib/libsmpeg.a、include/smpeg/*.h、bin/plaympeg、bin/smpeg-config

# 消费者用例（链接静态 libsmpeg，调用公开 C API）
SMPEG_VERSION(&v) 报告 0.4.5                                  ✓
SMPEG_new(不存在的文件) 返回对象                                ✓
SMPEG_error() 报告读取失败                                     ✓
SMPEG_status() == SMPEG_ERROR                                 ✓
SMPEG_getinfo() 报告空流                                       ✓
SMPEG_delete() 正常释放                                        ✓
SMPEG_CONSUMER_CHECKS=6 FAILURES=0
```

上游测试：smpeg 0.4.5-cvs20030824 **不含任何测试套件**（无 tests 目录、Makefile 无 `check` 目标/TESTS），
因此按 TEST_QUALITY_SPEC 在 `build()` 内置审计命令留证，并用消费者用例覆盖公开 API 的错误路径与对象生命周期。

## 注意事项
- 真实解码需要合法 MPEG-1 数据流；上游 tarball 不含样例文件，故消费者用例覆盖 API 契约与错误路径，
  解码正确性依赖上游代码本身（与上游一致，未改语义）。
- `plaympeg` 是 SDL 播放器，运行期需要显示/音频设备；CI 的 L2 冒烟只做非交互调用。

---

### 对话 #1 — 编译协作者 (implementer)

**请求**: 在鸿蒙 PC 上完成 smpeg 0.4.5-cvs20030824 适配，并附一条知识库草稿（路径 B），提交 PR。

**执行摘要**:
1. 依赖预检（W0/R36）：只需 `sdl/1.2.15`（制品仓已发布）。
2. 构建链路：2003 年 autotools + libtool → config.sub 补 aarch64/ohos → config.status umask 放行 →
   C++17 源码现代化（register / 窄化 / friend 声明）→ libtool C++ 运行时修正 → `conan create` rc=0。
3. 上游测试清点：无测试套件（N=0）→ build() 内置审计留证 + 6 条消费者断言。
4. 知识贡献（路径 B）：把"2003 年 C++ 代码在现代 clang + `-std=c++17` 下的三类硬错误
   （register 移除、列表初始化窄化、friend 声明作用域）"写成 kv+md 草稿。
5. 质量门禁：conan-verify、W3 本地 CI 模拟、W4 审计（见 `reports/`）。

**产出文件**: `conanfile.py`、`conandata.yml`、`patches/`（4 个）、
`test_package/`（`CMakeLists.txt`、`test_smpeg.c`、`conanfile.py`、`MANIFEST.yml`）、
`notes.md`、`manifest.yaml`、`commands.json`、`README.md`、`reports/test-report.md`、
`knowledge/drafts/DRAFT-legacy-cxx-modern-clang-cpp17-removals.{kv,md}`。
---

**编译结束**: 2026-10-04 14:31
**最终状态**: built
