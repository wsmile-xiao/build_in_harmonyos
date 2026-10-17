# elfutils 0.195.1 编译笔记（HarmonyOS PC · Conan autotools）

> 本版本 = 0.195 + **把 libdebuginfod 从 dummy 空壳改成真实客户端库**。
> 0.195 的其余内容（两个 musl 补丁、configure 探测注入、产物与 SONAME）
> 完全沿用，见下方「沿用 0.195 的部分」。

## 为什么递增版本而不是原地改

`--enable-libdebuginfod=dummy` 与 `=yes` 产出的 `.so` **同名同 SONAME**
（`libdebuginfod.so.1`）。原地改 0.195 会让同一个版本号的二进制内容发生
语义变化（dummy → 真库），且制品仓 `0.195` 已发布（R37/L0j）。故按仓库
惯例递增为 `0.195.1`。

## 本次核心变更

### 1. `--enable-libdebuginfod=dummy` → `=yes`
上游两个开关互相独立（`configure.ac:898-973`）：
- `--enable-libdebuginfod`：客户端库（`=no` 不建 / `=dummy` 空壳 / `=yes` 真库）
- `--enable-debuginfod`：服务端（需 libmicrohttpd + sqlite3 + libarchive）

服务端保持 `--disable-debuginfod`：OHOS PC 无 debuginfod 服务端运行时场景，
且「只建客户端」是上游支持的组合。

**dummy 与真库的实证差异**（0.195 已发布包 vs 本次构建）：

| | 0.195（dummy） | 0.195.1（真库） |
|---|---|---|
| `libdebuginfod-0.195.so` 体积 | 18880 B | 见构建日志（含 curl/json-c/elf 逻辑） |
| `DT_NEEDED` | 仅 `libc.so` | 增 `libcurl.so.4`、`libelf.so.1`、`libjson-c.so.5` 等 |
| `debuginfod_begin()` | 恒 `NULL` + `errno=ENOSYS`（`debuginfod-client.c:64`） | 返回可用句柄 |
| `bin/debuginfod-find` | 必然失败的客户端 | 可用 |

### 2. 新增依赖 curl / json-c——**且必须补 PKG_CONFIG_PATH**
configure 用 `PKG_CHECK_MODULES` 探测（`configure.ac:907-908`）：
```
PKG_CHECK_MODULES([libcurl],[libcurl >= 7.29.0],...)
PKG_CHECK_MODULES([jsonc],[json-c >= 0.11],...)
```
因此 `generate()` 新增 `PkgConfigDeps(self).generate()`，并把它的输出目录
（`self.generators_folder`）放在 `PKG_CONFIG_PATH` 首位。**不补则报**
`configure: error: unable to build libdebuginfod, missing libjson-c or libcurl`
—— 注意这是 `--enable-libdebuginfod=yes` 的硬错，不是静默降级。

为什么不能只把依赖包里自带的 `.pc` 目录塞进 `PKG_CONFIG_PATH`：
curl 包内那份 `libcurl.pc` 带 `Requires.private: openssl,zlib`，而本仓
`openssl` 包里**没有** pkgconfig 目录，pkg-config 解析不了该依赖就判定
libcurl「不存在」（实测 `Package 'openssl', required by 'libcurl', not found`
→ `checking for libcurl >= 7.29.0... no`）。`PkgConfigDeps` 会为整条依赖链
（含传递依赖）生成 `.pc`，是仓库既有做法（`acsccid` 1.1.13 /
`air-quality-sensor` 0.1.5 先例）。

另：依赖包内自带的 pkgconfig 目录作为第二顺位仍然保留，两者叠加更稳。

### 3. 构建期 `LD_LIBRARY_PATH` 必须覆盖**全部**依赖（含传递依赖）
configure 会编译并运行探测程序。新增 `-lcurl` 后探测程序连带
openssl/brotli/nghttp2/libssh2/zlib…，漏一个 libdir 就是
`configure: error: cannot run C compiled programs`。
仍坚持用 `LD_LIBRARY_PATH` 而非 `-Wl,-rpath`（后者会把 conan cache 绝对路径
烤进产物 RPATH）。

### 4. `package_info()` 把 `debuginfod` 纳入导出 libs
`['elf','dw','asm']` → `['elf','dw','asm','debuginfod']`：0.195.1 起产出的
`libdebuginfod.so.1` 是真实库，必须让消费者链得上它。
存量 `elfutils/0.195` 消费者精确 pin 到 0.195，不受影响。

> `pkg_config_name` 的取值方式**未改动**（仍是从 `lib/pkgconfig/` 里取第一个
> `.pc` 的 stem）。包内 `lib/pkgconfig/` 是 `libdebuginfod.pc` / `libdw.pc` /
> `libelf.pc`，按字典序首项是 `libdebuginfod` —— 0.195 的已发布包里同样是
> 这三个文件，故 `pkg_config_name` 前后一致，都不是本次变更的一部分。
> （该字段与包名不一致是 0.195 就有的既有形态，本次不动，避免超范围改动。）

### 5. test_package 扩到 27 条断言
原 15 条（libelf/libdw，含打开自身 ELF 读节区、dwfl 反查模块、错误路径）
+ 新增 12 条 libdebuginfod：
- `DEBUGINFOD_SONAME == libdebuginfod.so.1`
- **`debuginfod_begin() != NULL`** ← 这条直接区分真库/空壳
- `get_url`/`get_headers` 传输前为 NULL
- `set/get_user_data` 往返、`add_http_header`、`default_progressfn`
- `find_debuginfo`/`find_executable`/`find_source`/`find_metadata` 无服务端时
  离线返回 `-ENOSYS`（`debuginfod-client.c:1822-1829`，不触缓存不联网）
- `debuginfod_end`（含 NULL 保护路径）

测试离线确定性由测试程序自负：开头 `unsetenv("DEBUGINFOD_URLS")`，
并用 `argv[1]` 指定可写缓存目录，不写调用者 HOME。

### 6. 探测程序的运行期库路径改用 `Environment` + `save_script()`

0.195 的做法是直接改 `os.environ["LD_LIBRARY_PATH"]`。实测**不稳定**：同一配方
会出现「这次 configure 过了、下次 `cannot run C compiled programs`」。原因是 conan
自己生成的 `conanbuildenv-*.sh` 也在 export `LD_LIBRARY_PATH`，两边撞车，谁最后生效
取决于脚本聚合顺序。

改为 conan 明确支持的注入通道（仓库既有写法，`aaphoto` 0.45 / `dirb` 2.22 同款）：

```python
env = Environment()
for _dep in self.dependencies.values():
    for _p in _dep.cpp_info.libdirs or []:
        env.prepend_path("LD_LIBRARY_PATH", _p)
    for _p in _dep.cpp_info.bindirs or []:
        env.prepend_path("PATH", _p)
env.vars(self, scope="build").save_script("conanbuild_elfutils_probe")
```

对应的知识条目：`DRAFT-conan-dep-shared-libs-break-configure-conftest`
（机理链与判别口径写得很清楚，本包是该条目的又一实例）、`E467`
（`AutotoolsDeps` 把依赖闭包写进 LIBS，使最早的 `AC_PROG_CC` 探测就要加载整条闭包）。

### 7. `llvm-objcopy` / `binary-sign-tool` 必须 `env -u LD_LIBRARY_PATH`

**这是本次最隐蔽的坑**：`package()` 里签名日志一切正常
（`INFO - add codesign section success` / `write code sign data success`），
但装出来的 `.so` 一被 dlopen 就 `Permission denied`；包内自带的 `eu-readelf`
同样跑不起来；而**同一份文件在交互 shell 里手动签一次就好了**。

根因：`ohos-aarch64` profile 的 `[buildenv]` 会把 SDK 的
`/data/service/hnp/ohos-sdk.org/<sdk>/ohos/native/llvm/lib` 前置进
`LD_LIBRARY_PATH`（本配方 `generate()` 又加了全部依赖的 libdir）。而
`binary-sign-tool` 自身 NEEDED 的是**系统 libc++**（`std::__h` 内联命名空间），
被该变量带偏到 SDK 的另一份 libc++（`std::__1`）后，工具输出的签名 XPM 不认。
交互 shell 没有这个变量，所以「手动签成功、conan 内必挂」。

修法（全仓 22 个包在用，`cliquer` 1.21 / `concalc` 0.9.3 同款）：

```python
self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(...))
self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(...))
```

> 判定手法（3 分钟定性）：写个极小的 dlopen 探针（`clang x.c -ldl`）在 `$HOME/tmp`
> 里编译后运行——新编译的未签名二进制会落在 `u:r:adhoc_bin:s0` 域，这正是 XPM
> 校签名最严的上下文。用它 dlopen「本包新签的 .so」与「官方制品的 .so」做对照：
> 官方制品 OK + 本包 Permission denied ⇒ 就是签名没签好。
>
> ⚠️ 另一个反向陷阱：**别用 `llvm-objcopy --dump-section` 去读包内文件的
> `.codesign`** —— 该操作会**重写输入文件**，直接把签名弄失效（本次排查中因此
> 弄坏了 `curl` 包里的 `libcurl.so`，导致 configure 的 conftest 报
> `Error loading shared library libcurl.so`）。要读就 `readelf -x`，别 objcopy。

### 8. `lib/` 下的 SONAME 软链必须实体化（本次最关键的运行期修复）

上游 `install` 产出标准三段式命名，`.so` 与 `.so.1` 都是**符号链接**：

```
libelf.so -> libelf.so.1 -> libelf-0.195.so
```

OHOS 上这是**加载致命项**：ELF 的 `DT_NEEDED` 记的是 **SONAME**（`libelf.so.1`），
加载器按该名字 open 路径时若命中的是符号链接，在不具备符号链接解析能力的域下
得到 **EACCES**；而 musl 加载器只在 `ENOENT`/`ENOTDIR` 时才继续搜索下一个目录，
于是**立即整体失败、不再回退**：

```
Error loading shared library libelf.so.1: (needed by ./test_probe)
Error relocating ./test_probe: elf_version: symbol not found    → rc=127
```

实测判定（本机 dlopen 探针，跑在 `u:r:adhoc_bin:s0` 域，是 XPM 校签名最严的
上下文）：

| 加载对象 | 结果 |
|---|---|
| `libelf-0.195.so`（实体名） | **OK** |
| `libelf.so.1` / `libdw.so.1` / `libasm.so.1` / `libdebuginfod.so.1`（软链名） | **Permission denied** |

旁证：本机 conan 缓存里已发布的 `elfutils/0.195` 以及 30+ 个依赖包的 `lib/`
**全部是实体文件、0 软链**，唯独本包（新构建）是软链 —— 这也解释了为什么
0.195 的 test_package 里唯一那条 dlopen 断言（走的是实体名）没暴露此问题。

修法（`package()` 末尾加 `_materialize_soname_aliases()`，与
`archives/l/libkysdk-base/3.0.1.3` 同款；知识条目 **E316 / E492** 的 rec）：
`shutil.copy2` 跟随软链复制实体（保留权限位）→ 先写临时名再 `os.replace`
原子替换，避免删除系统调用。放在 `_sign_binaries()` **之后**：签名对象是真实
文件，副本随内容一起带走签名（「复制不破坏签名」是本仓 2026-08-04 真机对照
实验的结论，本次也复测确认）。

> 顺带解释了 `libelf.so.1` 这类软链为何连 `ln` 都建不出来（受限域拒绝
> `symlink()`）——**同一件事的两面**：该域既不认软链、也不让建软链。

## 沿用 0.195 的部分（此处只列要点，详见 `0.195/notes.md`）

1. **补丁 0001**：musl 无 `error.h`，`src/threadlib.c` 走上游既有的条件分支。
2. **补丁 0002**：`lib/eu-config.h` —— `_()` 按 `ENABLE_NLS` 分叉（musl 的
   `libintl.h` 是空壳）；`program_invocation_short_name` 别名到 BSD `__progname`。
3. **configure 探测注入**：依赖的 `-I/-L/-l` 经 `os.environ` 的
   `CPPFLAGS`/`LDFLAGS`/`LIBS` 喂给 configure（`extra_*` 不一定落到探测里）。
4. **umask 077 → 022**：上游 configure 带 `umask 077`，会让安装出的头文件
   对同组不可读。
5. **`--program-prefix=eu-`**、`--with-zstd`、`--disable-nls`、`--disable-werror`，
   以及 `-D_GNU_SOURCE` / `-DFNM_EXTMATCH=0` / `-Wno-error`。

## 本次新踩到的环境坑（已修，值得记）

**`configure` 报 `Error 126 Permission denied`：真因是受限 SELinux 域，不是执行位**
`autotools.configure()` 直接报 `Error 126 Permission denied`。一度按仓库里流传的
「HMDFS 复制丢执行位 / chmod 生效不可靠」解释，**本次实测证伪**：同一 build 目录里
`chmod 755` 后立刻 `./configure` 能正常 exec（模式也确实是可执行的），失败与模式无关。

真因（用一个只做「写脚本 + 直接 exec」的最小 conan 配方在秒级复现）：

```
驱动：用户存储的 python3（$HOME/usr/local/bin/python3）
  domain=u:r:adhoc_bin:s0
  -rwxrwx--- ... zz_script.sh          ← 模式没问题
  ./zz_script.sh        → /system/bin/sh: ./zz_script.sh: Permission denied   exec-rc=126
  /bin/sh zz_script.sh  → EXECOK                                              sh-rc=0
  ./zz_cfg.sh           → Permission denied                                  cfg-rc=126

驱动：bundle 的 python3（/data/storage/el1/bundle/libs/arm64/python/bin/python3）
  domain=u:r:develop_tools_hap:s0
  ./zz_script.sh        → EXECOK       exec-rc=0
  ./zz_cfg.sh           → rc=7（脚本自己的退出码）
```

即**受限域拒绝 exec 缓存目录里的文件**（普通文件/目录的创建与读写都正常）。
`sh <脚本>` 只**读取**脚本、不 exec 它，因此不受该限制 —— 修法就是仓库既有的
`CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh /system/bin/sh <configure> <args>`
（全仓 28 个包在用，如 `abx` 0.1）。`CONFIG_SHELL`/`SHELL` 同时指向该 shell，
保证 `config.status` 与 `config/install-sh` 子脚本走同一解释器（configure 内
`install_sh` 是 `${SHELL} .../install-sh` 形态）。

> 排查过程的可复用点：`config.log` 里 `./conftest` 之后紧邻的
> `Error loading shared library libX.so.N` 是「探测程序运行期缺库」；
> `Permission denied` 则先别急着归因执行位 —— 在本环境要先查进程的
> SELinux 域（`cat /proc/self/attr/current`）。两者都表现为
> `cannot run C compiled programs`，必须先看 `config.log` 才能分开。
> 域问题与 `ln -fs` 失败是**同一个根因**，见下一条。

**`ln -fs` 报 `Permission denied` 是环境问题，不是配方问题（未改配方）**：
elfutils 的 `libelf/Makefile` 链接规则里是裸 `ln -fs libelf.so libelf.so.1`
（`libelf/Makefile:1802`），构建到这一步报
`ln: cannot create symbolic link from 'libelf.so' to 'libelf.so.1': Permission denied`
→ `make[2]: *** [Makefile:1802: libelf.so] Error 1`。

定位过程（结论：**SELinux 域**）：
1. 先排除了 HMDFS「刚链接出的 `.so` 元数据未落定」——同一 build 目录里删掉产物
   重跑 `ln -fs` 稳定成功，`$HOME` 下「写完文件立刻建软链」也 8/8 成功。
2. 也不是 `ln` 选错了：`command -v ln` 在交互 shell 与构建 shell 里**同为
   `/bin/ln`**（→ `/system/bin/toybox`），且 `/usr/bin/ln`、`busybox ln`
   在交互 shell 里都正常。
3. 用一个最小 conan 配方（只 `self.run("ln -fs a b")`）在**秒级**复现了失败，
   然后在那个上下文里读 `/proc/self/attr/current`，拿到关键一行：
   ```
   attr: u:r:adhoc_bin:s0
   touch=0   mkdir=0   ln-path=1
   ln: cannot create symbolic link from 'a' to 'zz3': Permission denied
   ```
   即构建子进程落在 **`u:r:adhoc_bin:s0`** 域：**普通文件/目录创建放行，
   `symlink()` 被拒**，连 `/usr/bin/ln` 都被判「inaccessible」。
4. 触发点：`$HOME/.local/bin/conan` 的 shebang 是
   `#!/storage/Users/currentUser/usr/local/bin/python3`——**用户存储里那份
   未签名的 python3**。执行它会切换到 `adhoc_bin` 域；而 bundle 里的
   `/data/storage/el1/bundle/libs/arm64/python/bin/python3` 保持
   `u:r:develop_tools_hap:s0`。
5. 改为 `python3(bundle) $HOME/.local/bin/conan create ...` 后，域恢复
   `develop_tools_hap`，`ln -fs` 正常，构建继续。

> **结论：配方不需要任何 `ln` 规避，别加。** 这是**本地环境**的域配置问题：
> 谁用 `~/.local/bin/conan`（shebang 指向用户存储的 python3）跑构建，
> 谁就会在需要建软链的 autotools 包里撞上它。凡本仓必然要 `ln -s` 的包
> （elfutils 这类）都会命中，与 elfutils 0.195.1 的改动无关。
> 记录在此，避免下次重复排查。

> 顺带排除的两个假线索，也值得记：排查中途曾临时把 `ln` 垫片脚本挂到
> `PATH` 首位，结果是垫片自身在构建子进程里 exec 被拒（`/system/bin/sh:
> <shim>: Permission denied` → `Error 126`，垫片模式 `-rwxrwx---`），
> **把错误信息换成了另一种失败**，一度误导定位。`make` 报 `Error 126` 时
> 要读全那行：`/system/bin/sh: <路径>: Permission denied` 说的是**被调用的
> 那个文件**不可执行；而 `ln: cannot create symbolic link ...: Permission denied`
> 是命令自己返回的失败——两者都叫 `Permission denied`，出处不同、结论相反。

## 依赖

- 构建期/ELF 侧：zlib、zstd、bzip2、xz、argp-standalone、musl-fts、musl-obstack
- libdebuginfod 侧：**curl、json-c**（本次新增）

## 状态

built —— 本地 `conan create` 通过，test_package 27/27 断言全过
（libelf + libdw + 真实 libdebuginfod 均被真实调用）。

## 上游测试说明

上游 `tests/` 套件**在本版本被真实执行**（不再只靠 test_package 断言）：

```
make -k -j1 check-TESTS TESTS='<253 条>' check_PROGRAMS='<122 个>'
```

| 项 | 数量 |
|---|---|
| 上游 `TESTS`（`make --eval` 展开 `am__append_*` 后去重） | 259 |
| 上游 `check_PROGRAMS` | 128 |
| 因 OHOS musl 缺接口**无法构建** | 6 |
| 实际执行 | 253 |
| PASS / FAIL / SKIP | 221 / 26 / 6 |

- 跑不到的 6 条依赖 OHOS musl 未提供的 glibc 接口：`<error.h>`（2 个测试程序）
  与 `pthread_cancel`（4 个；OHOS musl 的 pthread.h 与 libc.so **都没有**该符号，
  上游 musl 本身是有实现的）。automake 的 `check-am` 依赖**全部**
  `check_PROGRAMS`，任何一个测试程序编不出来，整批用例都不会被执行 ——
  所以必须同时从 `TESTS` 与 `check_PROGRAMS` 里剔除；不这样做得到的是
  「0 条执行」而不是「253 条执行」。
- 26 条失败的逐条原因见同目录 `ohos-failure-analysis.md`，全部为平台/环境固有
  （ptrace 权限与 seccomp/SIGSYS、OHOS 无账号数据库、OHOS ELF 方言、fd 上限、
  musl getopt 差异、工具链输出基线差异），未发现与本次适配改动相关的失败。
- 0.195（基线包）从未执行过该套件，故不存在「0.195.1 引入回归」的可比基线。

### 让套件能在 OHOS 上跑起来的环境适配（均不改上游源码）

1. **`LD_LIBRARY_PATH` 必须含构建树自身库目录**：`src/Makefile` 里
   `AM_LDFLAGS = -Wl,-rpath-link,../libelf:../libdw` 只作用于**链接期**，
   运行期产物没有任何 RPATH。不给路径就是
   `Error loading shared library libdw.so.1: (needed by .../src/readelf)`，
   一次连带上百条用例失败。
2. **`LIBRARY_PATH` 供 `check_PROGRAMS` 链接**：这些程序的链接规则是
   `$(CC) $(CHECK_DEF_FLAGS) -o $@ … $(libelf_so_LDLIBS)`，**不含 `$(LDFLAGS)`**
   （上游假定依赖在系统默认路径），conan 依赖的 `-L` 上不了链接行 →
   `cannot find -lzstd`。用链接器标准搜索变量 `LIBRARY_PATH` 补。
3. **构建树 `lib/` 的 SONAME 软链实体化**：与 `package()` 的
   `_materialize_soname_aliases()` 同一原因（OHOS 加载器不跟随符号链接）。
   **必须在 check_PROGRAMS 构建完成之后再做**，否则可能被 make 变回软链。
4. **`wc` 兼容脚本（不引入 coreutils 依赖）**：`tests/run-strip-test.sh:56` 等 3 处用
   `wc --lines`（GNU 长选项），OHOS 的 toybox 与 hnp 的 busybox `wc` 都只认 `-l`
   → 13 条 `run-strip-*` 整批失败。修法：构建目录里生成一个 `wc` 脚本
   （GNU 长选项 → 短选项后转发系统 `wc`），**只在测试命令里**前置该私有目录。
   **不能改用 `tool_requires("coreutils/9.10")`** —— conan 会把 tool_requires 的
   `cpp_info.bindirs` **自动注入构建期 PATH**，于是 GNU `ln` 抢先被 autotools 的
   `$(LN_S)` 用上，构建直接挂（见下一节的域问题）。另外脚本必须有可执行位，
   而本机 `chmod` 常为空操作、无可执行位的文件会被 PATH 查找跳过 →
   先 `copy2` 系统可执行文件占位再覆写内容。
5. **清 `BASH_ENV`**：宿主 shell 的包装脚本会被 bash 子进程继承并污染
   （实测报 `... safe-delete-bash-env.sh: ... rm: ...: bad interpreter`）。

### ⚠️ 反直觉坑：**PATH 里不能出现用户存储（`.conan2/p/…`）里的 ELF**

`.conan2/p/…` 下的可执行文件是**未签名 ELF**，执行它会触发 SELinux 域切换到
`u:r:adhoc_bin:s0`，而该域**拒绝 `symlink()`**（普通文件/目录的创建读写正常）。
这也解释了为什么 `tool_requires(coreutils)` 会让构建死在

```
ln: failed to create symbolic link 'libelf.so.1': Permission denied
make[2]: *** [libelf/Makefile:1802: libelf.so] Error 1
```

实测对照（同一目录、同一 uid）：

```
/usr/bin/ln -fs a b            # 系统 toybox          rc=0 建链成功
<coreutils>/bin/ln -fs a b     # 用户存储里的 GNU ELF  rc=1  Permission denied
```

**规则**：PATH 里只允许系统路径 + 自己写的脚本目录；`rm`/`ln`/`rmdir` 一律系统版。

### 一个**未修**的平台现象（记录备查）

`src/stack` 的错误前缀来自 `error(3)`：上游基线期望 `basename(argv[0])`
（`stack:`），OHOS 实测是**完整路径**，4 条 `run-stack-*-test` 因此输出不匹配。
本仓 0002 补丁把 `program_invocation_short_name` 别名到 `__progname`
（已实测 `__progname` 确为 basename，别名本身正确），说明 `error(3)` 取值走的是
另一条路径。属**显示层**差异，不影响功能。
