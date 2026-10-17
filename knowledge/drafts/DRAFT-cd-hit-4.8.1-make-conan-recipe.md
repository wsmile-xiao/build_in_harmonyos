# DRAFT-cd-hit-4.8.1 — make 型库（纯 Makefile）的 conan 配方四要点

> 状态：草稿（供人工/AI 审核后 promote 为 E 条目）
> 来源：cd-hit 4.8.1 适配（2026-09-05），conan create G2 失败链
> 关联 KV：`DRAFT-cd-hit-4.8.1-make-conan-recipe.kv`

## 问题

cd-hit 4.8.1 是纯 Makefile 的 C/C++ 命令行工具（无 configure，Makefile 硬编码
`CC = g++`，`LDFLAGS += -lz -o` 的累加式写法）。conan create 依次出现三类失败：

1. **`ConanException: Error -11 while executing`（SIGSEGV）**：`generate()` 里
   `env.vars(self).save_script("conanbuild")` 与 conan 保留聚合脚本名 `conanbuild`
   冲突，生成自引用的 `conanbuild.sh`（内容为
   `. conanbuild.sh && . conanbuildenv-release-armv8.sh`），执行时无限递归直至 SIGSEGV。
2. **`make: *** No targets specified and no makefile found`**：`basic_layout()` 下
   源码落在 `source_folder`，而 `self.run` 默认 cwd 是 `build_folder`
   （如 `build-release/`），需要在 `self.run(..., cwd=self.source_folder)`。
3. **`clang-15: error: no such file or directory: 'cd-hit'`**：命令行传
   `LDFLAGS="-L<zlib>/lib"` 后，makefile 的 `LDFLAGS += -lz -o` 被整体忽略（命令行
   变量优先于 makefile 内 `+=`），链接命令末尾的 `-o cd-hit` 丢失，clang 把输出名当
   输入文件。

## 根因

1. conan 2.x 的 `save_script("conanbuild")` 名称与框架自动生成的聚合 env 脚本同名，
   生成逻辑认为“聚合脚本已被自定义覆盖”，写出自引用脚本。
2. `basic_layout()`：`folders.source = "."`（源码与 build 根同层），
   `folders.build = "build-release"`；`self.run` 默认 cwd = build_folder，
   纯 make 项目没有 `-f` 或 `-C` 时找不到 Makefile。
3. make 语法：**命令行变量赋值优先于 makefile 内的一切赋值**（含 `+=`），
   因此会把 makefile 里 `LDFLAGS += -lz -o` 覆盖为命令行值。
4. 硬编码 `CC = g++` 只能被命令行变量覆盖（makefile 内赋值不是 `?=`）。

## 方案（make-conanfile-quad）

```python
# generate()
from conan.tools.env import Environment
def generate(self):
    zlib_pkg = self.dependencies["zlib"].package_folder
    env = Environment()
    env.define("CPPFLAGS", f"-I{zlib_pkg}/include")
    env.define("LDFLAGS", f"-L{zlib_pkg}/lib")
    env.vars(self).save_script("cdhit_build_env")   # ← 唯一名，禁 "conanbuild"

# build()
def build(self):
    self.run(
        "make CC=clang++ CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib -j2",
        env="cdhit_build_env",          # ← 用同一唯一名
        cwd=self.source_folder,          # ← make 型项目务必指向源码目录
    )
```

- 依赖标志走 env 注入（makefile 的 `+=` 会对 env 值正常追加），**不要**在
  make 命令行传 `LDFLAGS=...`。
- tool 包：`package_type = "application"`，`package()` 拷二进制到 `bin/`，
  软件级 `commands.json`（R38）。
- `package_info()` 无 libs。

## 验证

- cd-hit 4.8.1：conan create G2 PASS（test_package 真实调用 `cd-hit -i ... -o ...`
  聚类 3 序列 → 断言 `.clstr` 含 2 簇）；W3 本地 CI（build_and_test.sh）L0 全通过、
  JC/KC pass、L5 bin/ 有产物。
- 本地 .work 探索编译 6 个二进制全部可运行，冒烟聚类正确。

## 适用边界

- 仅纯 Makefile（无 configure）C/C++ 工具库；autotools/cmake/meson 走各自生成器。
- 先读上游 Makefile 确认 LDFLAGS/CPPFLAGS 写法和 CC 赋值方式（`=` vs `?=` vs `+=`）。

## 反例与限制

- `save_script` 非保留名时不会崩溃；Makefile 用 `=`（非 `+=`）时命令行 LDFLAGS 覆盖安全；
- E540（runner-path-prepend）与本条目维度不同（那是 OHOS profile 工具链路径问题）；
- 网络侧：github.com 直连超时经 gh-proxy 拉取（E017 镜像注入），与配方写法无关。