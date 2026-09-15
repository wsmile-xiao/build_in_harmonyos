# opalmod 0.2.2.1 OpenHarmony adaptation

## Source

- URL: `https://deb.debian.org/debian/pool/main/o/opalmod/opalmod_0.2.2.1.tar.xz`
- 20292 字节；sha256 `c2b42bfc47caf8d37e7095cb8409944b59c12101ec0da6f87f867d985779c652`
  （与官方 Content-Length 逐字节一致）

## Adaptation

构建系统是 **Perl ExtUtils::MakeMaker**，结构较特殊：上游顶层 `Makefile` 不含真正的
构建逻辑，只是用 `for` 循环驱动 **5 个各自独立的子目录**：

```make
DIRS=po4a conf src                 # 顶层；src/ 下即 OpaL 模块
for part in where read dir manipulate action; do \
    (cd OpaL/$part; perl Makefile.PL INSTALLDIRS=vendor); \
    $(MAKE) -C OpaL/$part ...; \
done
```

适配要点：

1. **纯 Perl，无 XS** —— 实测 tarball 内 `.xs` 与 `.c` 文件数**均为 0**，故**无需编译器**，
   只有 `.pm` 产物需要安装。（这一点与 Data-UUID 等 XS 模块不同。）

2. **逐个驱动子模块** —— 配方用 `self.run(..., cwd=OpaL/<part>)` 逐个执行
   `perl Makefile.PL` / `make` / `make install`，等价于上游的 `for` 循环，
   但错误定位更清晰（哪个子模块失败一目了然）。

3. **用 `INSTALL_BASE` 而非 `DESTDIR`** —— 把 `INSTALL_BASE` 指向 build 目录下的
   绝对路径 `/lib/perl5` 作为 staging，`make install` 直接落到那里；
   与仓库既有 Perl 配方（Data-UUID）同一做法。

4. ★ **`package_info()` 按实际位置反推 `PERL5LIB`，不硬编码层级** ——
   MakeMaker 的最终落盘路径随 `INSTALL_BASE` / `INSTALLDIRS` 变化，可能是
   `lib/perl5`、`lib/perl5/<version>` 或 `lib/perl5/<arch>/…`。配方改为
   **glob 出 `OpaL/*.pm` 的实际位置**，取其上一级作为 `PERL5LIB`，
   避免"装好了但 Perl 找不到模块"。

R32 / R33：`settings.os` 判断用 `in ("Linux", "OHOS")`；不依赖未定义的 shell 变量。

## Verification

- `conan create`（`ohos-aarch64` profile）：**EXIT=0**
- 上游自测：**上游原样 4/5**（`where` 失败，见下「必需补丁」）→ **打补丁后 5/5**
- `test_package/run_opalmod_tests.py`：**11/11 通过**
  - 1 项：包内确含 `OpaL/*.pm`
  - 5 项：`OpaL::{where,read,dir,manipulate,action}` 均可被真实 `use` 加载
  - 4 项真实功能调用：
    · `OpaL::where::which('perl')` → 真实定位到可执行文件
    · `OpaL::read::readscalarfile()` → 读到预期内容
    · `OpaL::dir::getdirlist()` → 真实列出目录项
    · `OpaL::action` `setDebugLevel(3)`/`getDebugLevel()` → 取值往返一致
  - 1 项负向：加载不存在的模块必须失败（证明断言非恒真）

### 上游自测（5 个子模块的 test.pl，实跑结果）

| 子模块 | test.pl | 结果 |
|--------|---------|------|
| OpaL::where | 36 行 | `ok 1`（`which("perl")` 返回定义值）|
| OpaL::read | 32 行 | `ok 1` |
| OpaL::dir | 32 行 | `ok 1` |
| OpaL::manipulate | 32 行 | `ok 1` |
| OpaL::action | 32 行 | `ok 1` |

> 上游 `test.pl` 用 Test::Harness 的经典 `1..1` 协议（`BEGIN { print "1..1\n" }`
> + `END` 校验 `$loaded`），每模块 1 个用例，合计 5 个。
>
> **实测结果（上游原样）：4/5** —— `OpaL::where` 的 `test.pl` 失败，其余 4 个通过。
> 打上「必需补丁」后 **5/5**。

## 用途 / 与 debarchiver 的关系

`opalmod` 是 **debarchiver 的硬前置** —— Debian `control` 声明
`Depends: opalmod (>= 0.1.10)`，且 `debarchiver.pl` 在 **BEGIN 阶段**即
`use OpaL::action`，缺失则连 `--version` 都无法执行（实测
`Can't locate OpaL/action.pm` → `BEGIN failed`）。

故本包须**先行适配并发布**，debarchiver 才能适配（依赖任务先行的仓库惯例）。
