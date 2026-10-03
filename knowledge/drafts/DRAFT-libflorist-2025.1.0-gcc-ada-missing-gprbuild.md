# gcc-ada 缺 gprbuild/gprinstall，GPR 驱动型 Ada 库无法按上游路径构建

- **日期**: 2026-09-27
- **软件**: libflorist 2025.1.0（AdaCore/florist，HEAD `d28d09a6`）/ gcc-ada 9.5.0
- **门禁**: `conan create` → `build()` → 上游 Makefile 的 `floristlib-%` / `install-%` 目标
- **状态**: DRAFT（同 stem 配对 `DRAFT-libflorist-2025.1.0-gcc-ada-missing-gprbuild.kv`）

## 现象

libflorist 上游 `Makefile.in` 把构建与安装完全交给 GPR 工程工具：

```make
floristlib-%: force
	$(GPRBUILD) -p $(GPRBUILD_FLAGS) -XLIBRARY_TYPE=$* -Pflorist

install-%:
	gprinstall -Pflorist $(PROJECT_FLAGS) -XLIBRARY_TYPE=$* -a -p -f   \
		--prefix=$(PREFIX) --sources-subdir=floristlib             \
		--lib-subdir=floristlib --link-lib-subdir=floristlib       \
		--build-name=$*
```

而 ohpcd 的 `gcc-ada/9.5.0` **既无 `gprbuild` 也无 `gprinstall`**：

```
$ ls <gcc-ada包>/bin
aarch64-linux-ohos-c++  aarch64-linux-ohos-g++  aarch64-linux-ohos-gcc
aarch64-linux-ohos-gcc-ar  aarch64-linux-ohos-gcc-nm  aarch64-linux-ohos-gcc-ranlib
c++  cpp  g++  gcc  gcc-ar  gcc-nm  gcc-ranlib  gcc.ohos-wrapper  gcc.real
gcov  gcov-dump  gcov-tool
gnatbind  gnatchop  gnatclean  gnatlink  gnatls  gnatmake
```

`libexec/gcc/aarch64-linux-ohos/9.5.0/` 仅有 `cc1 cc1plus collect2 gnat1 install-tools lto-wrapper`。
制品仓层面同样无解：

```
$ timeout 60 conan list "gprbuild/*" -r=ohpcd
Found 0 pkg/version recipes matching gprbuild/* in ohpcd
```

## 根因

不是 PATH 没配好，而是**制品内确实不存在这两个可执行文件**。构建驱动（gprbuild）与
安装器（gprinstall）双双缺失，导致上游默认的 `make` / `make install` 路径在 OHOS 上
完全不可用。

## 处置（已验证）

在配方内接管构建与安装两个阶段：

1. **构建**：`gnatmake` 直编全部 Ada 单元，开关取自 `.gpr` 的 `Ada_Flags`
   （本库为 `-O2 -gnatp -gnat95`），`-D obj` 汇总对象与 ALI：

   ```sh
   gnatmake -c -f -gnat95 -gnatp -O2 -Dobj \
     -Ilibsrc -Ilibsrc/threads -Igensrc -Igensrc/threads -Iconfsrc <all .adb>
   ```

2. **归档**：`llvm-ar rcs lib/libflorist.a obj/*.o`

3. **安装**：自行实现 `gprinstall` 的语义——把 Ada 源规格（`.ads`/`.adb`）、ALI 与静态库
   放到上游 README 承诺的 `<prefix>/floristlib`，并安装一份 `Source_Dirs` 指向该
   subdir 的可用 `.gpr`（上游 `.gpr` 的 `Source_Dirs` 指向构建树，安装后不可用）。

4. **注意**：上游 `.gpr` 声明 `for Languages use ("C", "Ada")` 时，必须一并编译库内 C 单元，
   否则链接报 `undefined reference to 'store_errno'/'fetch_errno'`（libflorist 实例）。

## 证据

- `gcc-ada/9.5.0` 的 `bin/` 清单（上方实测输出）
- `conan list "gprbuild/*" -r=ohpcd` 返回 0 条
- 修复后端到端通过：`Package '21b17f8b…' created`
  （`archives/l/libflorist/2025.1.0/reports/conan-create.log`）

## 禁止事项

| 禁止 | 原因 |
|---|---|
| 注释掉/改写上游 Makefile 目标以绕开 gprbuild/gprinstall | 篡改上游交付物，且会丢掉 `LIBRARY_TYPE` 静态/共享分支与 gprinstall 的布局语义（`--sources-subdir`/`--lib-subdir`），消费者按上游文档找不到规格与库 |
| 因报错是 "not found" 就反复调整 PATH / 往 buildenv 里塞 gcc-ada 目录 | 制品内不存在该文件，PATH 永远补不出来，只会浪费 CI 轮次 |

## 相关条目

- `DRAFT-gcc-ada-missing-gnatprep-adb-p-preprocess` —— gcc-ada 缺 `gnatprep`（同源单点）
- `DRAFT-ada-gnats-native-only-toolchain-cross-build-trap` —— gcc-ada 仅 OHOS/armv8
- `DRAFT-adacgi-ada-source-library-conan-pattern` —— Ada 源码库适配模式
- `DRAFT-libgmpada-1.6-libgnat-static-non-pic` —— libgnat 非 PIC

## 溯源

task libflorist 2025.1.0 适配（分支 `feat/libflorist-2025.1.0`），2026-09-27 真机
`conan create` 实测。
