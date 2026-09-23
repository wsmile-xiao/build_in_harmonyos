# sdl-image 1.2.12 — autotools cross-compile on OHOS (draft)

**Category**: build-system | configure | ohos · **Severity**: 3 · **Tool**: configure/make/conan

## 症状

1. `configure` 归一化错误：`Invalid configuration 'aarch64-unknown-none'`（传 `--host=aarch64-linux-ohos` 时）。
2. 交叉构建被判为本地编译后，`config.status` 以 `./confXXXXXX` 相对临时目录工作，在 HMDFS 挂载上
   0700 目录不可写 → `config.status: ./confXxx/out: Permission denied`，Makefile 未生成。
3. 消费者编译报 `'SDL.h' file not found`：依赖 `sdl12-compat/1.2.68` 的 `cpp_info.includedirs` 为空
   （头文件实际在 `include/SDL/`），CMakeDeps 没有可导出的 include 目录。

## 根因

- 2012 年的 `config.sub` 早于 aarch64/OHOS，不认识 `aarch64` CPU 段与 `-linux-ohos` OS 段。
- `config.guess` 把构建机识别为 HarmonyOS 后，configure 认为无需交叉，于是走 conftest 运行检查路径，
  而该路径依赖 `mktemp -d`（0700）——本 worker 上 0700 目录不可写。
- 更隐蔽的一层：**无论是否交叉**，autoconf 生成的 `config.status` 都用
  `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，HMDFS 下该 0700 目录对构建进程不可写，
  于是 configure 打印"success"但 Makefile 从未真正生成（显式双三元组只能绕过 conftest，绕不过这一层）。
- 依赖元数据缺口：包目录里有头文件 ≠ cpp_info 导出了 include 目录。

## 处置（可复用）

1. **只补 `config.sub`**（aarch64 CPU 段 + `-linux-ohos` OS 段：maybe_os 列表与 OS 合法列表各一处，
   并在末尾 `-linux*)`（`sed 's|linux|linux-gnu|'`）改写分支之前加 `-linux-ohos)` 守卫分支），
   `config.guess` 保持原始，补丁最小化。
   实测：OS 合法列表条目本身已能阻止改写（`case` 首个匹配生效，该条目位于 `-linux*)` 之前；
   删掉该条目输出退化为 `aarch64-unknown-linux-gnu-ohos`），构建产物 `config.status` 记录
   `host_os='linux-ohos'`；守卫分支是在此之上的显式保险，写法对齐仓库先例（at/3.2.5、acpitool/0.5.1）。
2. **显式双三元组强制交叉**：
   `--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
   一次性绕开 config.guess 探测与不可运行的 conftest 检查（仓库既有先例：aalib 1.4p5）。
3. **补 `configure` 自身的 umask（与第 2 步并用，缺一不可）**：
   `sed 's/umask 077/umask 022/g' configure`（`patches/0002-configure.patch`）。
   configure 会把这段文本原样写进生成的 `config.status`，所以一处源码补丁同时修掉
   configure 期与 config.status 期：`config.status` 的临时目录由
   `(umask 077 && mktemp -d "./confXXXXXX")` 创建，HMDFS 下 0700 目录归 uid 20001006 且对构建
   进程不可写。实测：umask 022 建出的目录 `drwxr-s--x` 可写，umask 077 建出的
   `drwx--S---` 不可写（`./confW5skaH/subs-1.sed: Permission denied` → Makefile 未生成）。
   平台先例见知识条目 E011（所有 autotools 项目通用，非本包特例）。
4. **依赖头文件在消费者侧定位**：`test_package/generate()` 中用
   `self.dependencies["sdl12-compat"].package_folder` 计算 include 目录传给 CMake，
   不在被测包里越界声明别人的 cpp_info；依赖元数据修正应单独提 PR（PR 原子性）。

## 验证

`conan create`（ohos-aarch64, clang 15）通过；configure 命中 SDL/jpeg/png/tiff/webp；
`test_package` 8/8 通过，`IMG_Init()` 返回 `0x0f`。
