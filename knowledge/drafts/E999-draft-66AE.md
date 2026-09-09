# E999 — init-build 误判 autotools：手搓 Makefile 软件的配方写法（prover9 实证）

## 错误特征
init-build 输出 `BUILD_SYSTEM=autotools` 并按 autotools 模板生成 conanfile.py（AutotoolsToolchain +
`self.run("autoreconf")` 路径），但源码树根本没有 configure：
```
ERROR: autoreconf: 'configure.ac' or 'configure.in' is required.
# 或 conan create 阶段：No rule to make target 'configure'
```

## 触发条件
- 构建系统: 上游为手搓递归 Makefile（1990s 学术软件常见，如 prover9/LADR）
- 阶段: init-build 判型 → conanfile 生成 → conan create
- 实证软件: prover9 2017-11A（顶层 Makefile 递归 ladr/ → mace4.src/ → provers.src/ → apps.src/）

## 根因分析
init-build 的判型是启发式：仓库有 Makefile 又找不到 cmake/meson 探针时默认猜 autotools。
判型权威依据应是源码树探针：`find -maxdepth 2 \( -name 'configure*' -o -name 'configure.ac' \)`
为 0 且无 autogen.sh → 不存在 autotools 输入，模板必然失败。

## 解决方案

### 推荐方案
conan-init 生成骨架后**手动重写**为自定义构建配方：
```python
class Prover9Conan(ConanFile):
    package_type = "application"          # 43 个 CLI 工具，无库 API
    settings = "os", "compiler", "build_type", "arch"

    def build(self):
        # R33: 编译器从 profile 注入；上游 CFLAGS = $(XFLAGS) -O -Wall，
        # 附加标志必须走 XFLAGS（命令行覆盖 CFLAGS 会被子 Makefile 硬编码吞掉）
        cc = self.conf.get("build:compiler_executable", default="clang")
        self.run(f"make all -j1 CC={cc} XFLAGS='-fPIC -O2'")
```
package() 策略 B 手动布局：把 `bin/` 产物复制到 `${package_folder}/bin/`。

### 禁止做法
- ❌ 保留 autotools 模板硬跑 autoreconf（无 configure.ac，必然失败）
- ❌ 命令行传 `CFLAGS=...` 覆盖——子 Makefile `CFLAGS = $(XFLAGS) -O -Wall` 会直接丢弃注入值

## 验证
```bash
find ~/tmp/builds/prover9-2017-11A.work -maxdepth 2 -name 'configure*' | wc -l  # 0 → 非自 autotools
grep -n 'XFLAGS' archives/p/prover9/2017-11a/conanfile.py                      # 配方经 XFLAGS 注入
```

## 关联条目
- 相关: E999-B839（同款手搓 Makefile 的 install 并行竞态，同样 -j1 固化）
