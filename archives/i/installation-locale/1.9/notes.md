# installation-locale 1.9 适配记录

- **上游**：Debian Install System Team（`debian-boot@lists.debian.org`）的
  `installation-locale`，Debian **native 包**（`debian/source/format` =
  `3.0 (native)`），**没有独立于 Debian 之外的上游项目**，canonical 发布位置就是
  Debian 归档：`https://deb.debian.org/debian/pool/main/i/installation-locale/`。
- **源 URL 的取舍（重要，需复核）**：本仓库 preflight 的 PF7 源 URL 闸
  （`scripts/ohc/preflight.py::_pf7_classify`）把 `deb.debian.org` / `snapshot.debian.org`
  / `security.debian.org` / `archive.debian.org` 这四个主机字面量一律归入
  「Debian 下游重打包源」直接拦下。实测：

  ```
  https://deb.debian.org/.../installation-locale_1.9.tar.xz   -> "Debian 下游重打包源"（拦）
  https://ftp.debian.org/.../installation-locale_1.9.tar.xz   -> None（放行）
  ```

  故 `conandata.yml` 写 **ftp.debian.org**（Debian 自己的归档主机，ftp-master 的公开名，
  不是第三方镜像），两个 URL 实测返回**逐字节相同**的 tar.xz（sha256 均为
  `df78ab6906f2df9d6cbfba78584dd83b5498c7c53589dc77f43d2c7527f9bfda`）。仓库内已有
  14 处 `ftp.debian.org` 先例（如 `a/aldo`、`c/ca-certificates`）。**未做任何重打包**：
  不是 `+dfsg`，不是 `.debian.tar.*`，就是原生 orig tarball 本身。
- **交付**：`share/i18n/locales/C.UTF-8.in`（81642 字节 / 1410 行，与 Debian/glibc 的
  `/usr/share/i18n/locales/` 同形）+ `share/doc/installation-locale/{README,upstream/**}`
  + `licenses/LICENSE`，共 12 个文件 / 88926 字节。**纯数据包，无编译步骤**：
  `build()` 只做载荷指纹校验（文件数、总字节数、清单 sha256，见下），
  `package_info()` 把 `share/i18n` 前置进 `I18NPATH`。
- **为什么交付"定义源"而不是编译产物**：上游做的是
  `localedef -i C.UTF-8.in -f "UTF-8" ./C.UTF-8`（见上游 Makefile），产出
  `usr/lib/locale/C.UTF-8`。该编译需要 **glibc 的 localedef**，OHOS/musl 侧没有；
  且编译产物与架构相关。本包交付**与架构无关的 locale 定义源**并把上游配方原样带上
  （`share/doc/installation-locale/upstream/Makefile`），消费方按 glibc 约定自行编译。

## 载荷指纹（`build()` 硬校验，任一不符即 `raise ConanException`）

| 项 | 值 |
|---|---|
| 上游 tarball 展开后的普通文件数 | 10 |
| 上游 tarball 展开后的总字节数 | 85043 |
| `sha256("<名> <字节数>\n" 排序清单)` | `eca4fef1967aacdbdb8cda689eb4ef6f068f046f5a412feadc2a834b5f20bab9` |
| 数据本体 `C.UTF-8.in` | 81642 字节 / 1410 行 / sha256 `af4b0dad…c137c2` |
| 交付物总数 | 12 个文件 / 88926 字节 |

## 数据长什么样（`C.UTF-8.in`）

POSIX/glibc 的 locale 定义源，12 个 `LC_*` 类别：`LC_COLLATE`/`LC_MESSAGES`/
`LC_NUMERIC`/`LC_TIME` 是 `copy "POSIX"`，`LC_ADDRESS`/`LC_MEASUREMENT`/
`LC_MONETARY`/`LC_NAME`/`LC_PAPER`/`LC_TELEPHONE` 是 `copy "i18n"`，
`LC_IDENTIFICATION`（`i18n:2012`，revision `draft`）与 `LC_CTYPE` 是 inline 定义。
`LC_CTYPE` 占了 1338 行中的绝大部分，包含 11 个字符类别（含 `graph`/`print`/`punct`
三个上万码位的大表）、`toupper`/`tolower` 两个映射（各 749~759 对）、一个
`totitle` 映射，以及 `combining`/`combining_level3` 两个具名类。注释里写明数据是
**Unicode 3.2**（`gen-unicode-ctype.c` 生成，文件为 2001-2005 年产物）。

## 上游 N=0（清点证据）

源包里只有 `C.UTF-8.in`、`Makefile`（2 条目标：build / clean）、`TODO` 与 `debian/`
下 7 个打包元数据文件；**无 `test/`/`tests/` 目录、无测试框架、无 `check`/`test`
目标、无 `debian/tests/`（无 autopkgtest）**。Debian 侧 `debian/rules` 只有 `dh $@`，
`debian/install` 一行 `C.UTF-8 usr/lib/locale`。故本包的验证由
**消费者用例（89 项）** + **适配自检（16 条）** 承担，两者分列申报。

## 消费者用例（rule12）：`test_package/consumer_locale.py`（89 项，全绿）

纯 Python 实现一个 localedef 等价的读取器，把交付的定义源读成真实的表，再拿这些表
去处理真实文本，并与**两个独立实现**交叉核对：

1. `I18NPATH/locales/` 交付路径契约 → 读 `share/i18n/locales/C.UTF-8.in`；
2. localedef 等价解析：`comment_char`/`escape_char` 与行续接、12 个类别、
   `copy "..."`、`<Uxxxx>` / `..` / `..(N)..` 区间、`(a,b)` 映射对、具名 class/map 块；
3. LC_CTYPE 表重建：11 类 + 3 映射 + 2 具名类；
4. 真实查询：字符→类别（14 个探针）、类别→定义、码位→大小写（8 组）；
5. 端到端文本处理：201 个码位的混合语料（拉丁/希腊/西里尔/中日韩/TAB/NBSP/
   全角空格/ZWSP/非互逆大小写对/补充平面/emoji）→ 逐码位分类计数、按交付的
   `blank` 类切词、按交付的 `toupper` 映射折叠大小写，产出计数与 sha256 指纹；
6. 独立 oracle：
   - **(a) 上游参考实现 GNU libc**：`localedef --no-archive -i <交付文件> -f UTF-8`
     编译后用 `iswctype()`/`towupper()`/`towlower()`/`towctrans("totitle")` 探出的
     规模，作为 GOLDEN 钉进用例，纯 Python 重建必须**逐项相等**：
     14 个类别计数（749/760/90342/10/22/22/232622/232607/16/67/142253/90352/
     669/431）与 3 个映射规模（759/749/759）**全部一致**；
   - **(b) ISO C/POSIX 强制项**：`xdigit` 恰为 0-9A-Fa-f、`blank` 含 TAB/SPACE、
     ASCII 段 upper/lower 恰为 A-Z/a-z、`digit` 恰为 ASCII 0-9、`blank ⊂ space`；
   - **(c) Python 独立实现**：ASCII 段 26/26 与 Latin-1 段 58/58（toupper）、
     56/56（tolower）与 `str.upper()`/`str.lower()` **逐项一致**。

### 如实记录的落差（不是缺陷，是数据年代）

- 定义源是 **Unicode 3.2**（2005 年 glibc 数据）：全量比对下 `toupper` 有
  **28 个非 ASCII 对**与新版 Python `unicodedata` 不同（`toupper` 731/759、
  `tolower` 748/749 一致），用例把 28 这个数字**钉死并显式打印**——数据一换就会报出来。
- **Unicode 3.2 之后的码位完全不在任何类别里**：`U+1F600`（emoji，2015 年）
  `print`/`graph`/`alpha`… 全部为假，消费方必须回退。用例断言这一点成立。
- **19 对非互逆映射**（Unicode 事实）：例如 `toupper(µ U+00B5) = Μ U+039C`，而
  `tolower(Μ) = μ U+03BC ≠ µ`。用例断言该事实（`µ→Μ` 与 Python 独立实现结论一致）。
- `<0>` 占位符：文件在 Tamil（U+0BE6 在 Unicode 3.2 未分配）与 Ethiopic 两处写了
  `<0>;`。**实测**：把它删掉后用 `localedef` 重新编译，得到的 `LC_CTYPE`
  与原文**逐字节相同**（`cmp` 通过），即它不贡献任何码位；读取器识别但跳过它。

## 本地验证（真做过的事，逐项列明）

| 步骤 | 环境 | 结果 |
|---|---|---|
| `conan create`（recipe + test_package） | 本机 x86_64 / conan 2.29.1 / `CONAN_HOME=/tmp/conan-il`（隔离，未污染仓库） | **通过**：`build()` 三件套校验 OK；消费者 89 项 0 失败；自检 16/16 |
| 消费者用例 | 同上 | `89 项检查，0 项失败` |
| 适配自检 | 同上 | `16/16 assertions passed` |
| **上游参考实现往返**：`localedef --no-archive -i <交付文件> -f UTF-8 ./loc/C.UTF-8` | GNU libc 2.43 | 编译成功，产出 12 个类别文件（120961 字节） |
| **真实消费该编译产物**：`LOCPATH=./loc LC_ALL=C.UTF-8` + `isw*`/`tow*` 探针 | GNU libc 2.43 | `locale=C.UTF-8`，类别/映射规模即上面 GOLDEN 值 |
| **`I18NPATH` 契约** | GNU libc 2.43 | 不设变量 → `cannot open locale definition file 'C.UTF-8.in'`；设 `I18NPATH=<pkg>/share/i18n` → 编译成功（证明交付路径与 glibc 约定严格对齐） |
| `<0>` 语义判定 | GNU libc 2.43 | 删除 `<0>;` 后编译产物 `cmp` **逐字节相同** |
| `conan install --requires=installation-locale/1.9` | conan 2.29.1 | `conanrunenv` 里 `export I18NPATH="<pkg>/share/i18n:/usr/share/i18n"`（契约已挂进运行环境） |
| preflight | 本仓库 `scripts/ohc/preflight.py . main HEAD` | 见最终回复 |
| **未验证**：OHOS aarch64 真机/CI worker 上执行 | — | 本机没有 OHOS SDK；本包无编译步骤，风险点是 worker 的 Python 版本（用到的 `str.isascii()` 需 Python ≥ 3.7，conan 2 本身要求 ≥ 3.6） |
| **未验证**：OHOS/musl 上编译这份 locale | — | musl 没有 glibc 的 `localedef`；这也是本包只交付定义源、不交付编译产物的原因 |

## 溯源文件为什么一起交付

`share/doc/installation-locale/upstream/` 下原样保留上游 `Makefile`、`TODO` 与
`debian/` 7 个文件（changelog/compat/control/copyright/install/rules/source/format）：
它们不进任何运行路径，只用于复核"交付的确实是那份 Debian 源、用的确实是官方配方"。
自检里有一条断言专门检查上游 Makefile 的 `localedef -i $^ -f "UTF-8" ./$@` 原样保留。
