# ballandpaddle 0.8.1 — sdl_image / sdl_mixer / sdl_ttf 的头在 `include/SDL/` 下，`cpp_info` 却只声明 `include/`（草稿）

**Category**: build, autotools, sdl, conan, portability, probe-mismatch · **Severity**: 3 · **Tool**: configure|cc

## 症状

`configure` 一路绿灯 —— 包括这一行：

```
checking for IMG_LoadPNG_RW in -lSDL_image... yes
```

紧接着 `make` 的第一个翻译单元就炸：

```
/storage/.../b/src/main.cpp:29:10: fatal error: 'SDL_image.h' file not found
     #include "SDL_image.h"
              ^~~~~~~~~~~~~
ERROR: ballandpaddle/0.8.1: Error in build() method, line 113
    self.run(f"{prefix} MAKEINFO=/bin/true make -j1", env="conanbuild")
    ConanException: Error 2 while executing
```

迷惑点：**「依赖找到了」的日志刚刚打印过，头文件却找不到。** 看编译行会发现更诡异的事 ——
同一个命令行里既有正确的 `-I<prefix>/sdl12-compat/include/SDL`，又有三个只到
`include` 一层的：

```
-I<p>/sdl_i6806c92396375/p/include            ← sdl_image，少一层
-I<p>/sdl_m75bc569fbe221/p/include            ← sdl_mixer，少一层
-I<p>/sdl_t7b3837a31f5e9/p/include            ← sdl_ttf，少一层
-I<p>/sdl12eb04425fea651/p/include/SDL        ← sdl12-compat，正确
```

## 根因

两条独立的事实撞在一起：

**(1) `checking for ... in -lSDL_image... yes` 是纯链接探测，与头文件毫无关系。**
`AC_CHECK_LIB(SDL_image, IMG_LoadPNG_RW)` 展开后只做一件事：往链接行加
`-lSDL_image` 看能不能解析 `IMG_LoadPNG_RW` 这个**符号**。它不打开任何头文件，
也不检查 `-I`。所以这一行 `yes` 只能证明「库在、符号在」，**证明不了「头在搜索路径里」**。
把 `-lSDL_image` 删掉才是它唯一的失败信号。

**(2) 这三个包的公开头文件装在 `include/SDL/` 下，`package_info()` 却只声明了
`includedirs = ["include"]`。** 于是 `AutotoolsDeps` 忠实地按声明算出
`-I<pkg>/include` —— 差了一层。而它们的头是这样的：

```
<pkg>/include/SDL/SDL_image.h
<pkg>/include/SDL/SDL_mixer.h
<pkg>/include/SDL/SDL_ttf.h
```

它们各自的 `lib/pkgconfig/*.pc` 里写的**正是** `Cflags: -I${includedir}/SDL`：

```
$ cat <p>/sdl_i6806c92396375/p/lib/pkgconfig/SDL_image.pc
Cflags: -I${includedir}/SDL
```

也就是说 `include/SDL` 才是这三个包对外承诺的搜索路径，`cpp_info.includedirs`
的声明与它们自己的 `.pc` 不一致（漏了 `/SDL`）。

**为什么 `sdl12-compat` 没问题**：它声明的是 `includedirs = ["include/SDL"]`
（头也真在 `<pkg>/include/SDL/SDL.h`），所以只有它的 `-I` 是对的。同一个
`AutotoolsDeps` 里，正确与错误的 `-I` 并排出现 —— 这是定位本问题最快的线索：
**同族包的 `-I` 形态不一致，就是声明不一致。**

## 处置（可复用）

在 `generate()` 里，往 `AutotoolsDeps` **自己的 `environment`** 上追加
`CPPFLAGS`，补上缺失的那一层：

```python
deps = AutotoolsDeps(self)
deps.environment.append("CPPFLAGS", self._sdl_family_include_flags())
deps.generate()
```

`_sdl_family_include_flags()` 对每个已知布局异常的包，若
`<pkg>/include/SDL` 目录存在就产出一条 `-I<pkg>/include/SDL`：

```python
flags = []
for name in ("sdl_image", "sdl_mixer", "sdl_ttf"):
    folder = self.dependencies.host[name].package_folder
    include_dir = os.path.join(folder, "include", "SDL")
    if os.path.isdir(include_dir):
        flags.append("-I" + include_dir)
return flags
```

要点：

- **追加在 `deps.generate()` 之前**：`AutotoolsDeps.environment` 是惰性的，
  其官方文档即此用法（"If you need to modify some of the computed values you can
  access to the ``environment`` object."）。`Environment.append` 对列表值是
  `extend`，所以补出来的 `-I` 与它算出的 `CPPFLAGS` 合并成**同一条 export**，
  不存在「两个脚本互相覆盖」的顺序问题（conan 生成的脚本保留 `$VAR`）。
- **只补布局真的不对的包**：`sdl12-compat` 已声明 `["include/SDL"]`，重复补会
  产生重复的 `-I`（无害但脏）。判据就是「`<pkg>/include/SDL` 是否存在」+
  「`cpp_info` 是否已经指到它」。
- **不碰上游源码**：这是**包声明与包实际布局不一致**在消费者侧的补偿，
  给 sdl_image 之类的依赖打补丁、或改上游 include 写法都不对（见 forbid）。

### 怎么提前发现

写配方前逐个依赖做一次「声明 vs 实际」核对，成本极低：

```sh
# 1) 实际布局
ls <pkg>/include/SDL/            # 有 SDL_image.h → 头在 include/SDL
# 2) 声明给的 -I（build 目录里）
grep -o -- '-I[^ ]*' conanautotoolsdeps.sh | grep <pkg>
#    声明给出 -I<pkg>/include 而实际头在 <pkg>/include/SDL → 必然 fatal error
# 3) 包自己承诺的路径（最权威）
cat <pkg>/lib/pkgconfig/*.pc | grep -i cflags
```

以及一条通用判据：**`configure` 报「X found」而 `make` 报「X.h not found」时，
不要回头怀疑依赖没装 —— 去看那条「found」是哪一类探测。** 链接探测（`AC_CHECK_LIB`
/ `-l`）只管符号，头探测（`AC_CHECK_HEADER` / 直接编译）才管路径，两者失败点天然
分离。

## 退路

- **不想在消费者侧写死包名**：给这三个依赖包出修订版，把
  `cpp_info.includedirs` 改成 `["include/SDL"]`（与它们的 `.pc` 对齐），
  下游所有消费者一起受益。代价是要发新版本、且改动面比单包补偿大。
- **只缺个别头**：若绝大多数头在 `include/` 下、只有少数在 `include/SDL/`，
  用 `-I` 补两层即可（`include` 与 `include/SDL` 并存无害）。
- **不要**用 `sed`/补丁去改上游 `#include "SDL_image.h"` 为 `"SDL/SDL_image.h"`：
  那是把包布局问题写进上游源码，在所有正常布局的平台上（发行版 `libsdl-image1.2-dev`
  仍把 `<SDL_image.h>` 放在 `include/SDL/` 且用它自己的 `.pc` 补 `-I`）行为反而改变。

## 验证

- 修复前：`make` 在 `src/main.cpp:29` 报 `'SDL_image.h' file not found`；
  修复后编译行里三个包的 `-I` 都带上了 `/SDL`，该文件编译通过。
- 本地可只验证 `-I` 真的进了 `CPPFLAGS`：在 `generate()` 后 dump
  `deps.environment` 或 `grep -- '-I.*include/SDL' conanautotoolsdeps.sh`
  （应出现 4 条：sdl12-compat + 三个补出来的）。
- 提交后由 CI 实跑 `conan create` 验证（`fatal error` 之后不再有 `ERROR:`）。

## 关联

- `archives/b/ballandpaddle/0.8.1/conanfile.py`（`_sdl_family_include_flags()`）
- `archives/b/ballandpaddle/0.8.1/notes.md`（「构建处理」表对应行）
- 同族先例（同样是「依赖已注入，但探针/声明与制品不符」）：
  `DRAFT-7348-ballandpaddle-0.8.1-sdl12-compat-has-no-sdl-config`
  （探针找**可执行脚本** `sdl-config`）、
  `DRAFT-7348-ballandpaddle-0.8.1-ac-check-lib-probes-a-fixed-soname`
  （探针按**写死的 soname** 找库）
