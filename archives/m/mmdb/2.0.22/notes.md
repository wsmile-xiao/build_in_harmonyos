# mmdb 2.0.22 adaptation notes

## Software and source

- Software: CCP4 Coordinate Library `mmdb2` (macromolecular coordinate library: PDB / mmCIF / mmdb-native I/O plus the Model-Chain-Residue-Atom container model). Upstream home: https://www.ccp4.ac.uk. Language mix measured in the release tree: `mmdb2/` holds 33 `.cpp` and 34 `.h`; the remainder is autotools scaffolding. Zero external dependencies. Upstream distribution point measured on device: `https://ftp.ccp4.ac.uk/opensource/mmdb2-2.0.22.tar.gz` is a live directory listing (HTTP 200, 7020 bytes) carrying `mmdb-1.25.3.tar.gz`, `mmdb-1.25.5.tar.gz`, `mmdb2-2.0.1.tar.gz`, `mmdb2-2.0.5.tar.gz` and this package's `mmdb2-2.0.22.tar.gz`.
- Source URL and digest: `https://ftp.ccp4.ac.uk/opensource/mmdb2-2.0.22.tar.gz`, 4272184 bytes, SHA256 `70533e91565bf37cc14eb76304ac649fdbb0bd4694bbb07313a7c0ddbc4a94e2` - the mmdb2-2.0.22 release tarball as published on CCP4's own distribution server `ftp.ccp4.ac.uk/opensource/` (the site named by Debian's own `debian/copyright` `Source:` field and by the first `debian/watch` line; every endpoint probed is in the measurement table below). The digest comes from `sha256sum` on the build host for the file this run actually fetched, not from a catalogue. The tarball root directory is `mmdb2-2.0.22`, which does not match `name-version`, hence `strip_root=True`. Content equivalence was measured, not assumed: the previously used copy from the Debian pool (SHA256 `a9646933ce9f34633e1ae4901f2383af0e5318d6490851328f5b6aa06195ab51`, 737837 bytes) and this tarball were both unpacked and every file hashed - of 91 shared paths 88 are byte-identical, including all 33 `.cpp` and 34 `.h` under `mmdb2/`, `configure.ac`, `Makefile.am`, `mmdb2.pc.in` and the `COPYING*` licence texts; the 3 that differ are the generated autotools files `configure`, `Makefile.in`, `aclocal.m4`, and the official tarball additionally ships a 952-file `doc/` tree while omitting `build-aux/compile`. The recipe's in-place autoconf patch anchor was re-measured in the official `configure` (line 16691 of that file) and is still present.
  - Source-policy record (W4 round 1, P1-1): the first draft took the pristine upstream tarball from `deb.debian.org`, which this repository's PF7 source-URL gate names by host - `scripts/ohc/preflight.py` `_PF7_DEBIAN_HOSTS` at :361-362, `_pf7_classify` returning "Debian 下游重打包源" at :379-381 with no "disclosed therefore allowed" branch, and `check_source_urls` at :385-426 appending that verdict to the findings list. This revision neither routes around the gate with a hand-written mirror prefix (`_PF7_MIRROR_HOSTS` at :356-360 (measured this round for W4 round-2 P3-1: the symbol itself is on :356 and the host-list body runs :357-360; the earlier :359-360 was off) - writing a mirror by hand is itself an R39 violation) nor keeps the Debian host: it points at the upstream project's own server. Re-measured with that same classifier after the change: `_pf7_classify(new URL)` returns None, `_pf7_classify(old URL)` still returns "Debian 下游重打包源", and `check_source_urls` over this package's `conandata.yml` + `manifest.yaml` reports 0 findings (evidence: `~/tmp/uc2/z33-mmdb-fix2/rerun2.log` section [0], `PF7_RC=0`). Because the recipe revision changed (`cd7adaf7a4330206b4efafd1285df329`, `reports/conan-create.log:10`), `conan-verify`, the W3 local CI run behind `finish` and `graph validate` were re-run against this source; every report line number quoted in this file refers to that rerun.
- Licence bookkeeping: the tarball ships `COPYING` (GPL version 3 text, first line measured) and `COPYING.LESSER` (LGPL version 3 text), while the bundled README (self-labelled "Version 1.05 from 26.03.2004") describes the library as CCP4 "Part 0" software under "version 2.1 of the GNU Lesser General Public Licence". The recipe declares `LGPL-3.0-or-later`, matching the licence texts that actually ship, and both files are installed into `licenses/`.

## 取源端点实测表（W4 第 1 轮 P1-①：官方源穷举，逐条 HTTP 码与字节数）

全部在鸿蒙 PC B 机（`/storage/Users/currentUser`）用 `curl -sS -L` 实测（`--connect-timeout 20 --max-time 120`
用于 github/sourceforge/debian 面，其余 12/40）。原始逐条输出留在 `~/tmp/uc2/z33-mmdb-fix2/run-g1.log`、
`run-g2.log`、`run-g4.log`、`run-g3.log`、`run-src3.log`，本表是摘要。上一轮审计报的 github.com/ccp4/mmdb
「连接超时」本轮带超时重试得到的是 **HTTP 404**（超时不等于不可达，故重试并换 codeload 对照）：该仓库不存在。

| 端点 | 实测 | 结论 |
|---|---|---|
| https://www.ccp4.ac.uk/ | 200 / 38502 B | 首页可达，无源码发布链接 |
| https://www.ccp4.ac.uk/download/ | 200 / 33145 B | 只有各程序安装器链接（`download_file.php?pkg=...`），无 mmdb2 源码 tar |
| https://www.ccp4.ac.uk/dist/ | 404 / 30191 B | 无该路径 |
| https://www.ccp4.ac.uk/dist/mmdb-2.0.22.tar.gz | 404 / 30191 B | notes 首版预告的「官方 CCP4 download endpoint」形态不存在 |
| https://www.ccp4.ac.uk/dist/mmdb2-2.0.22.tar.gz | 404 / 30191 B | 同上 |
| https://www.ccp4.ac.uk/dist/mmdb_2.0.22.orig.tar.gz | 404 / 30191 B | Debian 命名在官方站不存在 |
| https://www.ccp4.ac.uk/dist/src/mmdb-2.0.22.tar.gz | 404 / 30191 B | 同上 |
| https://www.ccp4.ac.uk/dist/latest/ | 404 / 30191 B | 同上 |
| https://www.ccp4.ac.uk/mirrors/ | 404 / 30191 B | 同上 |
| https://www.ccp4.ac.uk/opensource/ | 404 / 30191 B | 发布面不在 www 主机，在 ftp 主机 |
| https://www.ccp4.ac.uk/software/mmdb/ | 404 / 30191 B | 同上 |
| https://www.ccp4.ac.uk/opensource/mmdb2-2.0.22.tar.gz | 404 / 30191 B | 同上 |
| https://ftp.ccp4.ac.uk/ | 200 / 9025 B | CCP4 自有 ftp 的目录树可达 |
| https://ftp.ccp4.ac.uk/dist/ | 404 / 196 B | 无该子目录 |
| **https://ftp.ccp4.ac.uk/opensource/** | **200 / 7020 B** | **目录内列有 `mmdb-1.25.3.tar.gz`、`mmdb-1.25.5.tar.gz`、`mmdb2-2.0.1.tar.gz`、`mmdb2-2.0.5.tar.gz`、`mmdb2-2.0.22.tar.gz` ⇒ 本包的官方发布面** |
| **https://ftp.ccp4.ac.uk/opensource/mmdb2-2.0.22.tar.gz** | **200 / 4272184 B** | **采用为本包取源；SHA256 `70533e91565bf37cc14eb76304ac649fdbb0bd4694bbb07313a7c0ddbc4a94e2`（本机 `sha256sum` 实测）** |
| http://ftp.ccp4.ac.uk/opensource/mmdb2-2.0.22.tar.gz | 200 / 4272184 B | 同一文件；未采用 - PF7 对明文 http 直接判「明文 http 源（R39 要求 https）」 |
| ftp://ftp.ccp4.ac.uk/opensource/mmdb2-2.0.22.tar.gz | rc=28，20 s 内连不上 21 端口 | FTP 端口对本机不可达，故取同机 HTTPS 形态 |
| https://www.ebi.ac.uk/ccp4/dist/ | 404 / 20544 B | EBI 侧无该镜像路径 |
| https://api.github.com/repos/ccp4/mmdb | 404 / 132 B | 仓库不存在 |
| https://api.github.com/repos/ccp4/mmdb/tags | 404 / 136 B | 同上 |
| https://api.github.com/repos/ccp4/mmdb/releases | 404 / 135 B | 同上 |
| https://api.github.com/orgs/ccp4/repos?per_page=100 | 200 / 145491 B | CCP4 组织仓库清单可达，其中无 `mmdb` |
| https://api.github.com/search/repositories?q=mmdb+org:ccp4 | 200 / 73 B | 命中 0 条 |
| https://github.com/ccp4/mmdb | 404 / 267915 B | 上一轮的「超时」重试后是 404 |
| https://github.com/CCP4/mmdb | 404 / 267915 B | 大小写变体同为 404 |
| https://github.com/ccp4/scons-dist | 404 / 267987 B | 无该仓库 |
| https://codeload.github.com/ccp4/mmdb/tar.gz/refs/tags/2.0.22 | 404 / 14 B | codeload 对照做了，同为 404 |
| https://codeload.github.com/ccp4/mmdb/tar.gz/refs/tags/v2.0.22 | 404 / 14 B | 同上 |
| https://codeload.github.com/ccp4/mmdb/tar.gz/refs/heads/main | 404 / 14 B | 同上 |
| https://raw.githubusercontent.com/ccp4/mmdb/master/configure.ac | 404 / 14 B | 同上（main 分支变体同为 404） |
| https://sourceforge.net/projects/ccp4/files/ | 404 / 57518 B | CCP4 在 SF 无 files 面 |
| https://sourceforge.net/projects/mmdb/ | 200 / 93426 B | 同名项目是 MaxMind DB，与本库无关 |
| https://downloads.sourceforge.net/project/ccp4/mmdb-2.0.22.tar.gz | 404 / 154 B | 无该发布 |
| https://gitlab.com/ccp4/mmdb | 403 / 5461 B | 组页 https://gitlab.com/ccp4 为 200，但无该发布 |
| https://download.savannah.gnu.org/releases/mmdb/mmdb-2.0.22.tar.gz | 404 / 371 B | 无该发布 |
| https://www2.mrc-lmb.cam.ac.uk/personal/pemsley/coot/dependencies/mmdb2-2.0.22.tar.gz | 200 / 737837 B | 逐字节等同旧 Debian 副本（SHA256 `a9646933ce9f34633e1ae4901f2383af0e5318d6490851328f5b6aa06195ab51`）；是 Debian `debian/watch` 的第二条在活行，但属项目成员个人依赖页而非上游发布面，故不采用，只作内容一致性对照 |
| https://deb.debian.org/debian/pool/main/m/mmdb/ | 200 / 15347 B | 旧取源面；`_PF7_DEBIAN_HOSTS` 点名主机，本轮弃用 |
| https://archive.debian.org/debian/pool/main/m/mmdb/ | 200 / 21685 B | 同为 Debian 主机族，不用 |

Debian 侧元数据（用于反查真正上游发布面，见 `run-g3.log`）：`mmdb_2.0.22-1.debian.tar.xz` 内
`debian/copyright` 第 4 行 = `Source: ftp://ftp.ccp4.ac.uk/opensource/`；`debian/watch` 第 2-3 行 =
注释掉的 `opts="passive" ftp://ftp.ccp4.ac.uk/opensource/mmdb2-(.*)\.tar\.gz` 与在活的
`https://www2.mrc-lmb.cam.ac.uk/personal/pemsley/coot/dependencies/mmdb2-(.*)\.tar\.gz`；
`mmdb_2.0.22-1.dsc` 的 Checksums-Sha256 段对 `mmdb_2.0.22.orig.tar.gz` 记 `a9646933ce9f34633e1ae4901f2383af0e5318d6490851328f5b6aa06195ab51` / 737837 B。
⇒ 两点结论：Debian 那份是逐字节未改动的上游原始发布树（`.orig` 只是改名）；上游文件名是
`mmdb2-2.0.22.tar.gz`（与 tar 顶层目录 `mmdb2-2.0.22`、`configure.ac` 的 `AC_INIT(mmdb2, 2.0.22)` 同形），
不是首版正文猜的 `mmdb-2.0.22.*`。

## Build system and package shape

- autotools only: one top-level `Makefile.am`, `configure.ac`, and `mmdb2.pc.in`. `configure.ac` runs `AM_INIT_AUTOMAKE([1.11 foreign subdir-objects silent-rules -Wall])`, `LT_INIT([disable-shared win32-dll])`, and `AC_SEARCH_LIBS([cos],[m])`.
- `disable-shared` is decided by upstream, so the package contains a static `lib/libmmdb2.a` and no `.so`. The recipe therefore exposes no `shared` option; the first draft declared `package_type = "library"` and `conan create` refused it with `ERROR: mmdb/2.0.22@ohpcd/stable: Package type is 'library', but no 'shared' option declared`, which is why it now declares `package_type = "static-library"`. A static-only package also gives CI gate G3 no `.so` basename to collide with.
- `AM_INIT_AUTOMAKE([-Wall])` is the automake warning option, not a compiler flag.
- Installed layout: `lib/libmmdb2.a`, headers installed by `pkginclude_HEADERS` into `include/mmdb2/` (PACKAGE is `mmdb2` from `AC_INIT(mmdb2, 2.0.22)`, verified against the built package tree), and `lib/pkgconfig/mmdb2.pc`. Hence `cpp_info.includedirs` lists both `include` and `include/mmdb2`, and `pkg_config_name` is `mmdb2` while the Conan package name stays `mmdb`.
- libm: configure reports `checking for library containing cos... none required` on this platform (musl resolves `cos` from libc). `cpp_info.system_libs = ["m"]` is kept because that is what upstream declares for the general case and the consumer links cleanly with it (measured through the test_package link).

## Three platform blockers found and fixed (each measured, no preventive patching)

1. Profile shell cannot resolve its working directory. `ci/conan/profiles/ohos-aarch64` exports `CONFIG_SHELL=SHELL=/data/service/hnp/bin/bash` (a symlink into `bash.org/bash_5.3`). Every Autoconf script then dies with
   `configure: error: working directory cannot be determined`
   preceded by `shell-init: error retrieving current directory: getcwd: cannot access parent directories` and `pwd: error retrieving current directory: ...`. Measured in the very Conan build directory, in its `src` sibling, and in a freshly created directory under `~/tmp`:
   - `/data/service/hnp/bin/bash -c pwd` → fails in all three, exit 1;
   - `/bin/sh -c pwd` (and the plain session `pwd`) → succeeds in all three.
   So the failing piece is that bash binary, **not** the depth of the Conan cache directory; the "deep `b/build-release` directory" attribution in `knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md` (and in `knowledge/doc/E386.md`, which is the same family) does not reproduce here. `conanbuild.sh` sources the profile buildenv *last* (verified in the generated script: toolchain, then deps, then `conanbuildenv-release-armv8.sh`), so no `AutotoolsToolchain`/`VirtualBuildEnv` assignment can beat it - the override has to be inline in the command. `build()`/`package()` therefore prefix every command with `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`.
2. `config.guess` shipped in the release tarball cannot identify this platform. Measured: `build-aux/config.guess[1477]: can't create $TMPDIR/cgXXXXXX/dummy.c: Permission denied` followed by `config.guess: unable to guess system type` with `uname -s = HarmonyOS` and a script timestamp of 2013-06-10. This is the E007 family (GNU config scripts have no HarmonyOS branch); E007 prescribes `perl scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub`, which is not usable from a recipe here: the helper is only reachable when `OHC_SKILL_ROOT` is exported (see `archives/a/abiword-plugin-docbook/3.0.8/conanfile.py`), it edits generated files (R6), and that old `config.sub` rejects the `ohos` triplet anyway (E072). The recipe instead passes an explicit `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl` pair, the same shape used by the merged `m4rie` / `4ti2` / `classads` recipes. build == host keeps autoconf on the native path (configure logged `checking whether we are cross compiling... no`), so run-if-else probes still execute instead of being silently skipped.
3. Autoconf scratch directory is unusable on this mount. After 1 and 2 were fixed, configure completed all checks and then died at
   `./config.status[1035]: can't create ./confMuXnpa/subs1.awk: Permission denied`
   抛错原文（拆成两段互不相邻的行内代码，是为了让本文件的既有状态解析器不把 `config.status` 后紧跟的冒号读成状态读数；两段原文均未改写）：脚本 `config.status` 报 `error: could not setup config files machinery`。
   Reproduced directly in the Conan build directory: `(umask 077 && mktemp -d ./confXXXXXX)` creates `drwx--S---` and the next `touch` inside fails with `Permission denied`, while `(umask 077 && mkdir ./pB$$)` and `(umask 000 && mktemp -d ./pDXXXXXX)` both create `drwxrws--x` and accept writes. So what makes the directory unwritable is the explicit mode 0700 that `mktemp -d` forces, on a tree where the login uid is not the owner shown by `ls`. The recipe replaces that one generated line inside `configure` at build time (`tmp=./conf$$-$RANDOM && (umask 000 && mkdir "$tmp")`), which is the shape proven on device and CI by `archives/c/cln/1.3.7`; it warns instead of silently continuing if the upstream pattern is absent. Attribution note for the pooled draft `DRAFT-6507-cln-mktemp-0700-hmdfs`: it claims "GNU mktemp -d always creates 0700, umask has no effect" - measured here, `umask 000` **does** change what the directory ends up as, so the "umask-only relaxation is useless" half of that claim did not reproduce on this device for this binary; the adopted fix (drop `mktemp` entirely) is unaffected by that difference.
   - Pre-scan false positives, recorded so nobody "fixes" them again: the `-Werror` flag is not used anywhere in this project - a full-tree grep for `Werror` gives exactly 3 hits and all three are comment text inside generated files (`configure:3882`, `configure:12300`, `aclocal.m4:334`, all "... or remarks (even with -Werror). So we grep stderr for any message ..."). Nothing had to be disabled from the configure or compiler-flag side and no `Makefile.am` was touched. The `dlopen` hit sits only in `m4/libtool.m4` / `build-aux/ltmain.sh`, i.e. generated libtool scaffolding, so it is not a capability observation about this library.
- No upstream source file was modified. Zero patches; the only in-place edit is the autoconf scratch-directory line in the generated `configure` described above.

## Upstream test inventory (five-dimension ledger)

Measured on the unpacked release tree `mmdb2-2.0.22` (the official CCP4 tarball adopted above: 1049 tar entries, 1043 files):
- `grep -rnE "TESTS|check_PROGRAMS|add_test" . --include=Makefile.am --include=*.ac` → **0 hits** (re-measured on this official tree, including the extra `doc/` subtree).
- `find . -name Makefile.am -o -name configure.ac -o -name "*.pc.in"` → **3 files**: `./Makefile.am`, `./configure.ac`, `./mmdb2.pc.in` (a single Makefile.am, so no per-directory test Makefile).
- tarball root listing → `AUTHORS COPYING COPYING.LESSER INSTALL Makefile.am Makefile.in README aclocal.m4 build-aux config.h.in configure configure.ac doc m4 mmdb2 mmdb2.pc.in`: **no `tests/` or `test/` directory** (the only addition over the previously hashed copy is `doc/`, 952 files).
- `find . -name "*.cif" -o -name "*.ent" -o -name "*.pdb" -o -name "*.gz"` → **0 hits**: the release ships no sample coordinate file that could be replayed either, and `mmdb2/` still holds exactly 33 `.cpp` and 34 `.h` in this tree.
- The only `.cpp` that looks example-ish, `mmdb2/mmdb_rwbrook.cpp`, is a file-format reader compiled into the library itself (it is listed in `mmdb2_libmmdb2_la_SOURCES`), not a registered test.
- Ledger: `N_static` = 0, `N_registered` = 0, `N_executed` = 0, un-executed classification = 0 (nothing exists to skip: the four measurements above are the evidence), `N_consumer` = 1 program with 84 assertions.
- `build()` still runs `make -j4 check`, so the automake check target is genuinely invoked; with an empty `TESTS` it executes 0 cases by construction rather than being silently omitted.

## Consumer test (`test_package/mmdb_consumer_test.cpp`, program `mmdb_consumer_test`)

- Compiles and links through `find_package(mmdb CONFIG REQUIRED)` / `mmdb::mmdb` against the installed package (dependency declared with `self.tested_reference_str`, no `tool_requires` on cmake) and is executed by `test()` via `self.run(bin, env="conanrun")`.
- Behaviour asserted (84 checks, deterministic, exit code decided by them):
  1. writes a hand-column-checked 3-atom PDB fixture (one chain A, one ALA residue; the fixture is authored by this recipe because upstream ships no sample file, see the inventory above - disclosed rather than presented as upstream data);
  2. `mmdb::Manager::ReadPDBASCII` returns `mmdb::Error_Ok` (logged value 0);
  3. resolves the parsed structure through public handles only - `Root::GetAtomI(1)` → `Atom::residue` → `Residue::chain` → `Chain::GetModel()` - and asserts `Model::GetNumberOfModels()==1`, `GetNumberOfChains()==1`, `GetNumberOfAtoms(false)==3`, `Chain::GetNumberOfResidues()==1`, `Residue::nAtoms==3`, `Model::GetChain(0)` returning the same chain pointer and `Model::GetChain(1)` returning none;
  4. asserts every parsed atom field: aligned names (`N`, `CA`, `C` after trimming the 13-16 column padding), element symbols (77-78), serial numbers, x/y/z within 0.001 of the fixture, occupancy and temperature factors;
  5. writes the model back with `WritePDBASCII` (returns `Error_Ok`; the library produced the name passed to it verbatim, `mmdb_consumer_written` - the probe list in the source keeps that honest), re-reads that generated file into a second handle and repeats checks 2-4 on it;
  6. table behaviour: `isAminoacid("ALA")` true / `"HEM"` false, `isSolvent("HOH")` true / `"ALA"` false, `isDNARNA("DA")==1` and `isDNARNA("ALA")==0`, `getMolecWeight("C")` inside (11,13) and strictly below `getMolecWeight("N")`, `getCovalentRadius("C")>0`, `getElementNo("N") > getElementNo("C") > 0`, `Get1LetterCode("ALA")=='A'`, `GetAAPIndex("ALA") != GetAAPIndex("GLY")`, `GetAAHydropathy("ALA")` within the documented -4.5..4.5 band;
  7. parser behaviour: `GetInteger("  42",4)==42`, `GetReal(" 3.250",6)==3.25`, `PutInteger(7,4)` producing `"   7"`.
- Two mmdb2 API traps found while writing it (library usability, not platform), useful for future consumers:
  - constructing `mmdb::Model(&manager, serial)` **after** a read yields a fresh, empty model: it reported `GetNumberOfChains()==0` and returned no chain for any index, while `GetNumberOfAllAtoms()` (a manager-wide query) reported 3. The parsed hierarchy has to be reached bottom-up from an atom handle; the model obtained that way reports the correct 1 chain / 3 atoms.
  - `Root::GetAtomArrayLength()` returns the allocated capacity, not the atom count - it reported 1001 for a 3-atom file, matching the 1-based `GetAtomI(index)` accessor rather than a length.

- **适配路径**：A（首版直接适配；B 判定由主理定案为 hit —— 本包三处平台机制与静态库报错面全部落在既有条目/草稿面内，不占知识位、不落新草稿，故路径 A 不变）
- **使用知识库**：hit，四面机制逐条对齐既有条目 —— (1) `CONFIG_SHELL`/getcwd 失败：`knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md:30` 给的是**命令内联** `CONFIG_SHELL=/bin/sh`（本包取这一形态），而 `knowledge/doc/E386.md:29-36` 给的是 **capability-tested shell**（从真实构建目录逐个探 shell、`pwd` 返 0 且无诊断才采纳，并在 conanbuild 之后重设 `CONFIG_SHELL`/`SHELL`）——同一机制面、两条不同处方，本包用的是前者，不得把 E386 说成内联处方；(2) 2013 版 `config.guess` 不认 HarmonyOS + 旧 `config.sub` 拒 `ohos` 三元组：`knowledge/doc/E007.md`、`knowledge/doc/E072.md`、`knowledge/drafts/DRAFT-E564-oldstyle-config-guess-ohos-reanchor.md`、`knowledge/drafts/DRAFT-autotools-config-sub-silent-ohos-triplet.md`；(3) `config.status` 临时目录在 hmdfs 上不可写：**同面已被该族条目记载**（`knowledge/drafts/DRAFT-6507-cln-mktemp-0700-hmdfs.md:20`、`:25-26` 及其 `.kv:1`、`:8`、`:16`、`:26-27`，`knowledge/drafts/DRAFT-kexec-tools-2.0.32-mktemp-setgid-2700-hmdfs.md:21`「显式 chmod 700/755/g-s 全部不生效」，`knowledge/drafts/DRAFT-hmdfs-mktemp-0700-append-deny.md:25-28`「ACL 在创建时定死、chmod 777 不能修复」），**但本包实测否证其「umask 无效」前提**（三臂矩阵见 blockers 第 3 条：`umask 000` + `mktemp -d` 落 `drwxrws--x` 且可写），所以这一组不是对既有条目处方的复用命中，而是**同面的处方争议**，按条目外偏差提请修正（见下节第 2 条），B 判定仍为 hit、不新建条目、不建 Issue；(4) 静态 only 库被 conan 拒（`Package type is 'library', but no 'shared' option declared`）：**唯一以该报错为其机制面的条目** `knowledge/doc/E283.md:11`（逐字报错行）与其处方 `:24`；限定（W4 第 2 轮 P3-2）：`knowledge/doc/E277.md:11` 的 error_signature 候选串里也并列同一行文本，但 E277 的根因（`:15` vendored 依赖未发布到 ohpcd）与处方（`:18-20` build-vendored-to-staging）与本报错不同面，故不并列为同面条目——「唯一」只限定机制面，不限定该行文本在全库的出现面。首版在此并列的 `knowledge/doc/E221.md`（CLI+公开库契约）、`knowledge/doc/E257.md`（header-only 需显式 `build()`）、`knowledge/doc/E277.md`（vendored 依赖在 build() 内编译）、`knowledge/doc/E321.md`（lite 系 header-only 的 Conan 2 迁移）经逐行核对与本报错机制**不同面**，本轮删去该并列引用。两处否证性读数（getcwd 与目录深度无关；6507 的「umask 无效」半句被本包矩阵否证）只作既有条目的修正提请，见下节；库 API 陷阱（读完后新建句柄得空模型、`GetAtomArrayLength()` 返回容量、`GetChain` 为 0 基）属使用注意事项，见上文 Consumer test 一节，不建条目
- **知识库扩展**：无新增条目（B=hit）—— (1)(2)(4) 三面命中既有条目/草稿；(3) 面同属该族条目已在池记载的机制面，本包贡献的是否证其「umask/chmod 无效」前提的读数，作为条目外偏差提请修正而不另立条目、不占知识位、不建 Issue；四面之外无新机制，故适配路径仍为 A
- **关联 Issue**：无需新建（B=hit）

## 条目外偏差提请（用于修正既有条目，不新建条目）

1. getcwd 失败与目录深度无关。池稿 `knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.kv:19-20`
   （正文 `knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md:33-34`）把处方写成"把构建放回源码目录内执行
   ……conan 缓存的 build-release 子目录在 HMDFS 上同样触发风暴，**浅一层即正常**"。本包在同一设备上按三种不同深度分别实测
   （深 Conan 构建目录、其 `src` 同级目录、`~/tmp` 下新建的浅目录）：`/data/service/hnp/bin/bash -c pwd` 三处全部 exit 1，
   `/bin/sh -c pwd` 三处全部成功 ⇒ 触发者是那个 bash 二进制本身，不是路径深度。**提请修正面**：把"浅一层即正常"降级为未经复现的旁证，
   保留与 `knowledge/doc/E386.md:33` 一致的处方（命令内联 `CONFIG_SHELL`/`SHELL`）。
2. "umask 无效"半句不成立（只指 `mktemp -d` 在本设备上的落盘模式）。池稿 `knowledge/drafts/DRAFT-6507-cln-mktemp-0700-hmdfs.kv`
   的 `:1`、`:8`（标题）、`:16`（keywords 行同时列有 `umask 无效` 与 `mkdir -m 0777`）、`:26-27` 与正文
   `knowledge/drafts/DRAFT-6507-cln-mktemp-0700-hmdfs.md:25-26`（"放宽后目录仍是 0700"）主张 umask 对 `mktemp -d` 不起作用。
   本包在 Conan 构建目录内的三条矩阵读数（原文见上文 blockers 第 3 条，同读数亦落在配方注释
   `archives/m/mmdb/2.0.22/conanfile.py:54-56`；本包未为该矩阵另存独立日志文件——`ls ~/tmp/uc2/z33-mmdb/` 实测该目录
   只有 verify/finish 过程日志与 probe 源码，没有矩阵专用日志；`grep -rl "umask 000" ~/tmp/uc2/` 本轮复算
   （W4 第 2 轮 P2-1 整改，2026-09-25 08:43 +0800 读数，清单快照 `~/tmp/uc2/z33-mmdb-fix3/umask_hits.txt`）
   命中 **17 个文件**，分类如下：本包 5 处全是 notes/配方的断点副本与整改脚本
   （`z33-mmdb/stage/conanfile.py`、`z33-mmdb/stage/notes.md`、`z33-mmdb-fix/fix_notes.py`、
   `z33-mmdb-fix/notes-closeout.md`、`z33-mmdb-fix2/z33edit2.py`），本包审计件 3 处
   （`z33-mmdb-audit/audit-result.json`、`z33-mmdb-audit2/audit-result.json`、`z33-mmdb-audit2/audit2_w4_input.json`），
   他任务件 9 处（`zhuli-10-xcmsdb/p53-patch.sh`、`p54-patch.sh`、`p55-patch.sh`；`z32-light-w4/verdict.up`、
   `z32-light-w4/audit-result-feat-light-1.2.2.json`；`z32-light-fix1/pull/audit.json`、`z32-light-fix1/apply_fix.py`；
   `z32-inputlirc-w4r2/report3.txt` 与二进制归档 `z32-inputlirc-w4r2/r2-bundle.tgz`）⇒ **17 处无一是本包三条矩阵的独立
   过程日志**，矩阵读数只存在于本文件与配方注释两处，故此处仍不虚构日志路径。上一版写「实测只命中 notes 与配方两处」
   与自家命令输出矛盾，本轮改为按实测计数加分类口径；第 2 轮判决件自报 16 并注明「计数只代表本轮读数时刻」，与本数的
   差额可由读数时刻临时件的增减解释（判决件自身即含该串，是候选差额之一）。命中集会随并发窗临时件增长——本整改件
   本身复算时也会多算入，复算请以上述快照清单对照，不得为对上数字删文件。
   - `umask 077` + `mktemp -d` → `drwx--S---`，随后写入报 Permission denied（不可写）；
   - `umask 000` + `mktemp -d` → `drwxrws--x`，可写；
   - `umask 077` + `mkdir` → `drwxrws--x`，可写。
   与池面一致的部分：0700 型目录在这棵 setgid 树下对登录 uid 不可写；最终处方（弃 `mktemp`，改 `umask 000 && mkdir`）
   照 `archives/c/cln/1.3.7` 的形态生效。**被否证的部分**仅是"umask 放宽不改变落盘模式"这一句——本设备上 `umask 000`
   确实改变了 `mktemp -d` 的结果模式（与兄弟窗在案的"差异不在 mktemp 实现、在 hmdfs 改写 mode"同向）。
   **提请修正面**：把 6507 的机制归因从"mktemp 恒 0700、umask 无效"改为"hmdfs 对 0700 目录的写拒绝（uid 错位语义）"，
   并保留 `mkdir -m 0777` 与 `umask 000` 两条可选处方。

## 适配过程记录（对话条目）

按真实步骤序列记录；每条给证据文件路径，未单独留日志的步骤已注明，不补造时间与结果。

### 对话 #1 首稿与包形态定形
- 取源与校验：`~/tmp/uc2/z33-mmdb/mmdb_2.0.22.orig.tar.gz`（737837 字节，SHA256
  `a9646933ce9f34633e1ae4901f2383af0e5318d6490851328f5b6aa06195ab51`，本机 `sha256sum` 产出），
  解包根目录 `mmdb2-2.0.22` 与 name-version 不一致 ⇒ `strip_root=True`。
- 首稿按 `package_type = "library"` 声明被 conan 拒（原文见「Build system and package shape」第 2 条），改 `static-library`。
  证据：`archives/m/mmdb/2.0.22/conanfile.py`、`archives/m/mmdb/2.0.22/reports/conan-create.log`。

### 对话 #2 config.guess / config.sub 不认平台
- 读数 `build-aux/config.guess[1477]: can't create $TMPDIR/cgXXXXXX/dummy.c: Permission denied` +
  `config.guess: unable to guess system type`（`uname -s` = HarmonyOS，脚本时间戳 2013-06-10）。
  证据：本文 blockers 第 2 条；解包树留在 `~/tmp/uc2/z33-mmdb/mmdb2-2.0.22/build-aux/`。
- 处置：显式 `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`，不编辑生成文件（避 R6）。

### 对话 #3 CONFIG_SHELL / getcwd
- 三处深度矩阵读数（bash 失败、`/bin/sh` 成功）见 blockers 第 1 条与「条目外偏差提请」第 1 条；该步为 shell 级实测，
  未单独留日志文件，读数以本文记录为准。处置：`build()`/`package()` 每条命令内联 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`。

### 对话 #4 config.status 临时目录
- 三条 umask/mktemp/mkdir 矩阵见「条目外偏差提请」第 2 条。处置：就地替换生成脚本 `configure` 的一行
  （old/new 对见 `archives/m/mmdb/2.0.22/conanfile.py:76-77`），上游模式缺失时告警而不静默继续。

### 对话 #5 静态 only 与本地门禁
- `conan create` 通过（`reports/conan-create.log`，本轮 recipe revision `mmdb/2.0.22@ohpcd/stable#cd7adaf7a4330206b4efafd1285df329`，见 create:10）；
  `preflight_check.sh mmdb/2.0.22` 零依赖 rc=0；PF7 源 URL 闸对本包 `conandata.yml`/`manifest.yaml` 报 0 条（见上文 Source-policy record）。
- **三一致的口径（W4 第 1 轮 P2-1 整改）**：逐条 `## G0:`–`## G4:` 判决行**只存在于**
  `archives/m/mmdb/2.0.22/reports/conan-verify-report.md`（G0:8、G1:17、G2:31、G3:35、G4:39，`**Verdict**` 行在 :3）。
  本轮 W3 日志 `archives/m/mmdb/2.0.22/reports/w3-local-ci.log` 全文 `Verdict` 行数 = 0（本轮复算
  `grep -c Verdict` = 0，全文 567 行）；它真实拥有的判决行是 8 枚 `*_RESULT=` 标记，逐行读出的原文依次是：
  `G0_RESULT=pass`（w3:23）、`KC_RESULT=pass`（w3:63）、`JC_RESULT=pass`（w3:90）、
  `L0_RESULT=pass: all checks passed`（w3:553）、`L1_RESULT=pass: upstream tests + test_package executed`（w3:554）、
  `L2_RESULT=skip: no bin/ dir`（w3:555）、`L4_RESULT=pass: patches clean`（w3:556）、
  `L5_RESULT=pass: lib/ has content`（w3:557）；另有 Build Summary（w3:561）与收尾成功行（w3:566，原文为
  `[step] All packages built and tested successfully` 结尾带一个 ✅）。W4 第 2 轮 P2-2 整改：上一版把 w3:63、w3:90、
  w3:553、w3:555、w3:556、w3:557 标成 `[step]` 前缀、把 w3:554 标成 `conancenter:` 判决行、把 w3:23 标成 `$`，
  均为误标——`[step]` 只出现在步骤标题行（如 w3:21、w3:24），`[ok]` 是其下的明细行（如 w3:22、w3:25），
  这八枚 `*_RESULT=` 行不带这两种前缀。凡引用「G0–G4 全绿」一律指认 verify 报告的上述行号，不得写成「W3 的 G0–G4」。
  另注意 W3 的 `G0_RESULT=pass`（w3:23）那条 G0 是**知识图谱完整性检查**：标题行 w3:21 为
  `[step] G0: Knowledge graph integrity check...`，明细行 w3:22 为 `[ok] G0: Knowledge graph integrity check passed`
  （540 entries）——上一版把这条 `[ok]` 记作 w3:21，本轮按实读改为 w3:22。该 G0 与 verify 报告的 G0
  （知识命中/预构建风险评估）**同名不同物**，两者不得互为佐证。

### 对话 #6 消费者测试 84 条断言
- 上游 0 注册测试的四条清点见「Upstream test inventory」；消费者程序 84 断言、0 失败、rc=0。
  证据：`archives/m/mmdb/2.0.22/test_package/mmdb_consumer_test.cpp`、standalone 复算件
  `~/tmp/uc2/z33-mmdb/probe.cpp`、`~/tmp/uc2/z33-mmdb/probe2.cpp`、`~/tmp/uc2/z33-mmdb/standalone/consumer`。

### 对话 #7 W3、finish 与本轮收口
- 真 W3 日志：`archives/m/mmdb/2.0.22/reports/w3-local-ci.log`；上一轮 finish：
  `~/tmp/uc2/z33-mmdb/finish1-20260925-054405.log`（该轮 `:75` 打印状态不一致告警、`:76` 打印无对话记录告警）。
- 本轮收口动作：3+2 回填为 hit（见上）、把状态解析器的触发串拆成不再相邻的字面、新增本小节；
  重跑日志落 `~/tmp/uc2/z33-mmdb-fix/`（该轮 finish 同样红在 G0 干净构建验证与 step5b/step8，见
  `finish2-20260925-055716.log` 的 `:29`、`:106`）。换源后的第二次重跑落 `~/tmp/uc2/z33-mmdb-fix2/rerun2.log`，
  其 `FINISH_RC=2` 的逐项披露见下文「未覆盖与告警披露」第 5 条。

### 对话 #8 断点与交接件
- 上一棒断点：`archives/m/mmdb/2.0.22/.handoff.json`（`step_failed` = Step6，恢复命令为 finish mmdb 2.0.22 built）；
  配方与 notes 的断点副本在 `~/tmp/uc2/z33-mmdb/stage/`。


## 未覆盖与告警披露（W4 第 1 轮 P2-② / P3-① / P3-③；第 2 轮 P1-1 的 finish 未绿披露）

- **G0 点名的已知风险 E490 未在配方中处理（如实披露，本轮不修）**：`conan-verify` 在
  `reports/conan-verify-report.md:11` 打印「已知风险 E490 未在配方中处理」，修复建议见 :14
  （`chmod +x configure config.guess config.sub install-sh missing`，框架预扫方案 `restore-known-autotools-script-modes`，
  并附 :15 的「G2 conan create 可能因此失败」预警）。本包**没有**按该建议改任何文件权限位：配方只就地替换生成脚本
  `configure` 里的 autoconf 临时目录创建行（`conanfile.py:76-77` 的 old/new 对）。判据是本轮实测 - G2 conan create 判 PASS
  （`reports/conan-verify-report.md:31`），W3 里 config.status 的建表与执行阶段全部通过（w3:285-288），
  没有出现可执行位类失败。所以这条是**未处置的框架预扫风险**，不是本包的现实故障；披露口径以本条为准，
  别处不再写「E490 已处理」。
- **verify 报告 L2/L4/L5 三节图标与正文相反，不构成证据**：`reports/conan-verify-report.md:42` 的 L2、
  :45 的 L4、:48 的 L5 标题图标写 ✅ PASS，正文却均为「⏭️ 跳过（无 cache 路径）」（:43、:46、:49）。
  本轮口径改为「图标 PASS 而正文为跳过 ⇒ 不构成证据」；消费者程序的真依赖证据只来自 W3 的 L1e 破坏性反证
  （w3:546、w3:549，先跑通再把 `lib/`、`include/` 移走确认判失败）与 `test()` 运行读数（w3:535）。
  同理 W3 的 `L2_RESULT=skip: no bin/ dir`（w3:555）是静态库包的框架预期，既非失败也不可当作可执行证据。
- **verify 报告 G4 的「⚠️ 无法找到程序包 ID」**（:40）：G4 标题仍判 PASS，该告警是框架侧取不到 package id 的输出，
  本包证据不依赖它（产物与安装以 `reports/conan-create.log`、W3 的 `L5_RESULT=pass: lib/ has content` 为准）。
- **消费者程序的退出码只看 `g_failures`，不校验 `g_assertions` 下限**（`test_package/mmdb_consumer_test.cpp` 的
  `#define CHECK` 在 :31、`if (g_failures != 0) return 1` 在 :197）：若 CHECK 宏被改坏成空操作，程序仍会返 0。
  账面 84 有本轮运行期同文读数背书（`reports/conan-create.log:133` 与 `reports/w3-local-ci.log:535` 各一次），
  故按 W4 判决件记为账面 nit。本轮**不改测试代码**：改 `test_package` 同样动构建输入、会作废刚重跑的证据链，
  收益只是账面形式。
- **本轮 finish 未绿：`FINISH_RC=2` 的逐项原样披露（W4 第 2 轮 P1-1；上一版对本轮只字未提）**：本轮收口的
  `finish mmdb 2.0.22 built` **没有通过**。一手证据 `~/tmp/uc2/z33-mmdb-fix2/rerun2.log`（30429 B / 370 行，本轮实测，
  mtime 2026-09-25 06:49）逐行照录：`:67` `Step 3/10: G0 干净构建验证...`、`:68` `❌ G0: 找不到原始 tarball`、
  `:69` `⚠️ G0 干净构建验证失败，请手动检查构建结果`、`:70` 提示另跑 `ohc-run.py clean-verify`；
  `:106` `目录缺失: packaging`、`:107` `缺少 release tar.gz`、`:108` `缺少 debug tar.gz`、
  `:110` `finalize 完成，有 2 个缺失 + 0 个一致性问题`、`:111` `finalize-archive 有警告 (RC=2)`；
  `:129` `❌ 知识图谱完整性检查发现 1 类问题`（`:116`-`:119` 点名 E219/E253/E305 三个 `.kv` 的 root_cause/rec_approach
  为空字段，属仓库存量知识条目，不是本包文件）；`:134` `⚠️   gen_summary 失败: 'str' object has no attribute 'append'`（Step 8/10 生成 SUMMARY.md 的框架侧异常）；
  `:139` `❌ test-report.md — 需创建 reports/test-report.md`、`:140` `❌ packaging/ — 需创建 packaging/ 目录并打包`、
  `:141` `❌ .staging-verified — 需创建 .staging-verified 空文件`、`:143` `⚠️ 3 项未就绪，submit 前需修复`、
  `:145` `⚠️ 失败步骤: step5b, step8`、`:173` `FINISH_RC=2`。
  **只照录不圆说**：同一日志 `:158` `EXIT_REASON: finish_success`、`:159` `EXIT_CODE: 0`、`:160` `STEP_FAILED: Step6`
  三行与上面的红互不相容，本轮读源码定性为框架侧硬编码——`scripts/ohc/finish.py:533` 把 `is_blocking` 写死为 False，
  `:536-538` 据此固定印出该三行，与相应步实际成不失败无关；`:145` 的失败步骤取自 `self.steps`
  （`step5b` 见 `:327-333`、`step8` 见 `:408`），`:570-571` 再以 `all(self.steps.values())` 决定内层返回 1；
  `FINISH_RC=2` 是包裹层把内层 rc=1 转写成 2（`~/tmp/uc2/build-slot.sh:156`）。另 `finish.py:344` 在 gen_summary
  抛异常的分支里仍把 `step6` 置 True ⇒ `:134` 的失败不进 `失败步骤` 清单，属框架计数口径，本包不改框架件。
  **不是本轮换源引入的回归（换源前后同形）**：同一失败集在换源前两轮的日志里逐字同形——
  `~/tmp/uc2/z33-mmdb/finish1-20260925-054405.log` 的 `:33`、`:34`（G0 找不到原始 tarball / 干净构建验证失败）、
  `:78`（finalize-archive RC=2）、`:101`（gen_summary 失败）、`:110`（3 项未就绪）、`:112`（失败步骤 step5b, step8）、
  `:127`（STEP_FAILED: Step6）；`~/tmp/uc2/z33-mmdb-fix/finish2-20260925-055716.log` 的 `:29`、`:30`、`:72`、`:95`、
  `:104`、`:106`、`:121` 同形。且 rerun2 里预构建风险评估那条 G0 仍判 PASS（`:19`、`:80`）⇒ 该 G0 红属框架既有状态，
  本包不把它定性成自身编译失败，也不据此改取源。
  **不阻塞本 PR 的判据（均为本轮实测，不引用审计读数）**：`test-report.md` 位于 `reports/` 内，而 `reports/` 整目录被
  `.gitignore:96` 的 `reports/` 规则忽略（`git check-ignore -v` 对本包该路径命中此条）⇒ 它本就不可能进 PR；
  `.staging-verified` 被 `.gitignore:228` 的 `**/.staging-verified` 忽略，是本地标记件（框架用法见
  `scripts/ohc/dispatch.py:270`、`:305` 与 `scripts/ohc/finish.py:75-81`）；`packaging/` 未被忽略，但按
  `git ls-tree -r --name-only origin/main -- archives` 复算，origin/main 的 7750 个版本目录中只有 75 个带
  `packaging/`（0.97%）⇒ 静态库归档不带它属仓内主流形态。
  **本轮没有创建 `packaging/`、`.staging-verified`、`test-report.md` 中的任何一件**：前两件是不进 PR 的本地/可选产物，
  为凑绿而造没有证据价值；`test-report.md` 缺本轮真跑证据（上游 0 注册测试，账面只有消费者程序一条），造出来就是假证据。
  **finish 的 RC 与本轮阻塞门禁的绿证互不覆盖**：`rerun2.log:35` `VERIFY_RC=0`、`:100`-`:101`（W3 本地 CI 通过，日志即
  `archives/m/mmdb/2.0.22/reports/w3-local-ci.log`）、`:137`（W2 仅含配方变更 10 文件、无框架文件）、`:355` `GRAPH_RC=0`、
  `:7` `PF7_RC=0`；finish 的 RC=2 落在上述 step5b（存量 `.kv` 字段）与 step8（三项本地产物）两个非编译门禁的告警步上，
  未出现编译或链接类失败。本节据 `conan-verify` 与 W3 报告判可交付，**不宣称 finish 通过**。



**最终状态**
- 构建：`conan create` 通过，产出 `lib/libmmdb2.a`、`include/mmdb2/*.h`、`lib/pkgconfig/mmdb2.pc` 与 `licenses/`（判决行以本轮 `reports/conan-verify-report.md` 为准）。
- 上游测试：`N_static` 0 / `N_registered` 0 / `N_executed` 0，`make -j4 check` 已在 `build()` 中真实调用；"确无注册测试"的四条清点命令见上。
- 消费者测试：`mmdb_consumer_test` 84 条断言，0 失败，退出码 0（standalone 复算与 test_package 内运行同源）。
- 补丁：0 个上游源码补丁；唯一就地修改是生成脚本 `configure` 里的 autoconf 临时目录创建行。
- 代号：主理-33（本棒为适配执行段，PR / 台账 / B 判定收口归主代理）。
---

**编译结束**: 2026-09-25 06:47
**最终状态**: built
- 状态: built（可编译/可安装/可执行，与本级归档清单的 built 判定同值）
