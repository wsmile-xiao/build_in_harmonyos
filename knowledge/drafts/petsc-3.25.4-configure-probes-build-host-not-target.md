# petsc 3.25.4：configure 探测的是构建主机，不是目标平台——构建树名要用 `--with-petsc-arch` 钉住，X11 要用 `--with-x=0` 关掉

> Draft: DRAFT-PETSC-3254-CONFIGURE-PROBES-BUILD-HOST-NOT-TARGET
> Stem: `petsc-3.25.4-configure-probes-build-host-not-target` — 与本名 `.kv` 成对

## 基本信息

- **ID**: DRAFT-PETSC-3254-CONFIGURE-PROBES-BUILD-HOST-NOT-TARGET
- **严重度**: 3
- **类别**: conan-recipe-configure
- **触发工具**: configure|make|conan
- **阶段**: configuration|build|testing

## 错误特征

两种症状，同一个根因（以为 configure 看的是目标平台）：

```
# (a) 构建树名对不上
gmakefile:72: arch-ohos-c-opt/lib/petsc/conf/files: No such file or directory
make: *** [GNUmakefile:17: .../arch-ohos-c-opt/include/petscconf.h] Error 2

# (b) 主机的 X11 被编进静态库，消费者被迫 -lX11
/usr/bin/ld: xinit.c:(.text+0x9fc): undefined reference to `XGetGeometry'
/usr/bin/ld: xioerr.c:(.text+0x25): undefined reference to `XSetIOErrorHandler'
/usr/bin/ld: xtone.c:(.text+0x23a): undefined reference to `XSetForeground'
```

(b) 更隐蔽：直到**消费方链接**才爆出来，而且只在装了 `libX11-dev` 的 worker 上复现
——同一个配方在 A worker 过、B worker 挂，看起来像抖动而不是配方 bug。

## 根因分析

### (a) 构建树名来自 `sys.platform`

`config/PETSc/options/arch.py:29-40`：

```python
def setNativeArchitecture(self):
    arch = 'arch-' + sys.platform.replace('cygwin','mswin')   # 构建主机！
    arch += '-' + self.framework.argDB['with-clanguage'].lower().replace('+','x')
    arch += '-debug' if self.framework.argDB['with-debugging'] else '-opt'
```

`configureArchitecture()` 的优先级是：`-with-petsc-arch` > 命令行 `PETSC_ARCH=` >
环境变量 `PETSC_ARCH` > `nativeArch`。

配方如果只在 `make` 行写 `PETSC_ARCH=arch-ohos-c-opt`，而 configure 用的是
`nativeArch`，在 Linux 构建机上就得到 `arch-linux-c-opt`——两个名字分家，
make 去一个**从未创建过**的目录里找 `petsc/conf/files`，直接 Error 2。

### (b) `--with-x` 探的是主机的 X11

PETSc 的 `--with-x` 默认自动探测，探的是**构建主机**的头文件/库。
worker 上有 `libX11-dev` → X 画图后端被编进 `libpetsc.a` → `PetscInitialize`
注册 viewer 时引用到这些对象 → 连只算范数的消费方也必须带 `-lX11`。

OHOS 上根本没有 X11，这些后端纯属负担。

## 解决方案

**主方案**: pin-the-arch-name-and-disable-host-autodetected-x

```bash
python3 ./configure \
  --prefix=$PREFIX \
  --with-cc=clang --with-cxx=clang++ --with-fc=0 --with-mpi=0 \
  --with-petsc-arch=arch-ohos-c-opt \   # ← 与 make 用同一个名字
  --with-x=0 \                          # ← 别把主机的 X11 编进来
  --with-scalar-type=complex --with-precision=double \
  --with-shared-libraries=0 --with-debugging=0 \
  --download-f2cblaslapack=1 \
  COPTFLAGS='-fPIC -O2' CXXOPTFLAGS='-fPIC -O2'

make PETSC_DIR=$SOURCE PETSC_ARCH=arch-ohos-c-opt all
make PETSC_DIR=$SOURCE PETSC_ARCH=arch-ohos-c-opt install
```

名字钉死后，配方不再依赖 worker 的 `sys.platform`，configure 与 make/install
两个阶段永远一致。

## 适用范围与推广

- 所有 PETSc 配方（`petsc`、`petsc-complex`，以及将来的精度变体）；
- 更一般地：**凡是"构建目录名或能力探测来自 native probe"的 configure 系工程**：
  - autotools 用 `config.guess` 决定构建目录名；
  - CMake 用 `CMAKE_HOST_SYSTEM*` 拼路径；
  - 任何"跑一个本地小程序就断定目标平台有某能力"的探测。
- 通用动作：为每个 configure 系包列出**哪些决定是 native probe 做的**，交叉构建前
  逐一显式钉死，不要让"worker 上碰巧装了什么"决定产物。

## 验证

本机（x86_64 + gcc，`sys.platform == 'linux'`）实测：

```bash
# (a) 复现：按"只在 make 行写自定义名"的老写法
python3 ./configure --with-cc=gcc ... # 不带 --with-petsc-arch
# → PETSC_ARCH: arch-linux-c-opt
make PETSC_DIR=$PWD PETSC_ARCH=arch-ohos-c-opt all
# → arch-ohos-c-opt/lib/petsc/conf/files: No such file or directory  (Error 2)

# (b) 复现：不带 --with-x=0
gcc -I$PFX/include -I$PFX/include/petsc test.c -L$PFX/lib \
    -Wl,--start-group -lpetsc -lf2clapack -lf2cblas -Wl,--end-group -lm -lstdc++ -o t
# → undefined reference to `XGetGeometry' / `XSetIOErrorHandler' / `XSetForeground'

# 修复后
python3 ./configure ... --with-petsc-arch=arch-ohos-c-opt --with-x=0
# → PETSC_ARCH: arch-ohos-c-opt；make 成功；消费者无需 -lX11
# → test_package 断言 12/12 全过
```

## 关联条目

- 配套条目：`petsc-complex-3.25.4-self-contained-complex-blas`（自包含 BLAS 与
  `petscconf.h` 传播 ABI 宏）、
  `petsc-complex-3.25.4-abi-variant-separate-conan-package`（变体为何独立成包）
- 同族：`petsc/3.25.3`（同一 configure 流程，未踩到这两点）
