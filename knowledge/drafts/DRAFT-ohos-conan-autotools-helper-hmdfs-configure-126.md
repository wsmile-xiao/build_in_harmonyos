# Draft: Conan Autotools helper 在 OHOS 真机的替代写法 — autotools.configure() 直接 exec ./configure 报 126（HMDFS 无执行位）；手写 CONFIG_SHELL 调用时 configure 又不在 self.build_folder（basic_layout 的 generators 目录）

> Source event: `esekeyd/1.2.7` 真机 shadow CI r2/r3/r4（2026-09-29，r5 全绿）。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## 问题（两连环，都在手写/半手写 autotools 配方时触发）

### ① autotools.configure() 直接 exec ./configure → Error 126

```text
esekeyd/1.2.7: RUN: ".../b/configure" --prefix=/ ...
/system/bin/sh: .../b/configure: Permission denied
ERROR: ... Error in build() method
        autotools.configure()
ConanException: Error 126 while executing
```

conan.tools.gnu 的 `Autotools.configure()` 以**直接 exec** 方式运行 configure
脚本。构建缓存目录在 HMDFS（/storage/…/p/b/<hash>/b），脚本文件没有执行位
（chmod 在 HMDFS 上不生效，E046/E087），exec 报 126。这不是 configure 内容
问题——同一脚本用 `bash <path>` 跑就正常。

### ② 改成 self.run("bash ./configure", cwd=self.build_folder) → No such file or directory

```text
esekeyd/1.2.7: RUN: bash ./configure --prefix=/ ...
bash: ./configure: No such file or directory
```

`basic_layout` 下 `self.build_folder` 是 **generators 目录**
（…/p/b/<hash>/b/build-release，conanbuild.sh 所在处），而 conan create
从 source 缓存复制出来的源码树（含 configure）在**上一级** …/p/b/<hash>/b。
Autotools helper 内部会自己解析这个位置；手写 `self.run` 时必须自己找。

## 根因

两个坑叠加把"用标准 helper"逼成"手写调用"，而手写调用又暴露了布局知识：

1. HMDFS 拒绝对无执行位文件 exec（126），`bash <script>` 显式解释执行是唯一通路
   （rotix r1 已验证同法）；
2. Conan 2 basic_layout 的 build_folder≠源码副本根，configure 位置有两个候选
   （build_folder 的上级副本、或 source_folder），helper 不在时需自行探测。

## 修复（配方内，零基础设施改动）

```python
def _conf_dir(self):
    # configure 由 conan 复制到 build base（…/b），basic_layout 的
    # self.build_folder 是其下的 generators 目录（…/b/build-release）；
    # source_folder 是 source 缓存（…/s）。逐候选探测，两个环境都对。
    for cand in (self.build_folder, self.source_folder):
        if os.path.isfile(os.path.join(cand, "configure")):
            return cand
    raise ConanInvalidConfiguration("configure script not found")

def build(self):
    apply_conandata_patches(self)
    config_shell = os.environ.get("CONFIG_SHELL", "bash")  # profile buildenv 注入
    conf_dir = self._conf_dir()
    prefix = "/"  # DESTDIR 风格
    args = f"--prefix={prefix} --bindir={prefix}/bin --sbindir={prefix}/bin ..."
    self.run(f"{config_shell} ./configure {args}", cwd=conf_dir, env="conanbuild")
    self.run("make -j1", cwd=conf_dir, env="conanbuild")

def package(self):
    self.run(f'make install DESTDIR="{self.package_folder}"',
             cwd=self._conf_dir(), env="conanbuild")
```

configure/make/install 全部钉到同一 conf_dir，产物经 DESTDIR 落到
package_folder，bindir/sbindir 归一收进 bin/。

## 排查顺序（真机 autotools 包 conan create 失败速查）

| 症状 | 阶段 | 条目 |
|---|---|---|
| `permission denied: bash`（build_and_test.sh 的 KC/G0e 行号） | CI 门禁，包构建之前 | opencsg 草稿：job PATH 缺 /data/service/hnp/bin → ssh 启动 runner 前 `export PATH=/data/service/hnp/bin:$PATH` |
| `configure: Permission denied` + `Error 126` | conan build | 本条 ① |
| `bash: ./configure: No such file or directory` | conan build | 本条 ② |
| `config.status: ./confXXXX/out: Permission denied`、`sed: can't read Makefile` | configure 已过、Makefile 未落盘 | E011/E052/E129：umask 077 补丁 → 000（rsyslog 8.2404.0 判例） |
| `getcwd: cannot access parent directories` 刷屏 | configure 一启动 | classads/cvsgraph 草稿：hnp bash 在 HMDFS 深路径 getcwd 损坏，按能力探针换 /system/bin/sh |

## 验证（esekeyd/1.2.7，真机 r2→r5 逐项实证）

- r2 复现 ①（126）；r3 复现 ②（No such file）；r4 复现 umask 表；
- r5（本条修法 + 补丁 0002 umask）：conan create 成功、test_package 14/14、
  L0/L1/L4/L5 pass、L1e genuine、exit 0。

## 边界

- 该写法是 Autotools helper 的替代，不是补丁：不修改上游 configure，
  不修改 ci/ 基础设施；
- `env="conanbuild"` 必须带（CC/CFLAGS/PATH 由 AutotoolsToolchain 生成）；
- 若 CONFIG_SHELL 指向 hnp bash 且出现 getcwd 刷屏，回退 classads/cvsgraph
  的 /system/bin/sh 方案（设备差异，先跑能力探针）。

## 关系

- similar_to: opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path（同为
  环境供给，但那条是 runner PATH，本条是配方内 shell 调用与目录探测）
- complement: E087（HMDFS 无执行位）、E046（chmod 不生效）、E011/E052/E129
  （config.status umask）、E037/E049（shebang/绝对路径）、
  DRAFT-rotix-…-gcc-probe-shim（CONFIG_SHELL 显式调用的首个判例）、
  classads/cvsgraph（CONFIG_SHELL 的 getcwd 反例）
- 查重声明：E087 面向 install 落盘脚本；cvsgraph/classads 面向 shell 能力
  （getcwd）；opencsg 面向 runner PATH。**「Autotools helper exec 126 +
  basic_layout configure 目录探测 + 手写调用模板」无既有条目**。
