# DRAFT-20001: conan tool_requires autoconf 在 OHOS 的 perl ABI 陷阱（PATH 必须前置 conan 包 bin）

- 条目主题：配方 `build_requirements()` 声明 `tool_requires("autoconf/x.y")` 并在 build() 里跑 `./autogen.sh`（或其他裸 autoconf 调用）时，OHOS 上必须把 conan autoconf/perl/m4 包的 `package_folder/bin` 前置到 PATH，否则双 perl 版本混用崩溃。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：yate 6.4.1；同范式适用于所有 autogen.sh 自举类配方（工具链依赖 autoconf 的包）。

## 错误特征
- `Cwd.so: Perl_my_cxt_init: symbol not found`（autoconf 进程崩溃）
- 崩溃发生在 autogen.sh 生成 configure 之前，无 configure 产物

## 根因
1. conan autoconf 包的 `bin/autoconf` 是 `#!/bin/sh` 包装脚本：`: "${PERL:=perl}"; exec "$PERL" "$here/.autoconf-real" "$@"` —— perl 解析**走 PATH**。
2. 系统 `/data/service/hnp/bin/autoconf` 的 shebang 固定指向 hnp perl 5.42.0；conanbuild 环境的 `PERL5LIB` 指向 conan perl 5.42.2 的 lib。
3. PATH 未前置 conan 包 bin 时：系统 autoconf（hnp perl 5.42.0 解释器）+ conan PERL5LIB（5.42.2 的 Cwd.so）→ 跨版本加载 perl 模块 → ABI mismatch。

## 修复
```python
def _tool_path_prefix(self):
    bins = []
    for name, dep in self.dependencies.build.items():  # 已含传递 build 依赖
        b = os.path.join(dep.package_folder, "bin")
        if os.path.isdir(b):
            bins.append(b)
    return os.pathsep.join(bins)

def build(self):
    prefix = self._tool_path_prefix()
    cmd = f'PATH="{prefix}:$PATH" ./autogen.sh' if prefix else "./autogen.sh"
    self.run(cmd, cwd=self.source_folder)
```

## 验证
- yate 6.4.1 conan-verify G2：不注入 PATH → `Perl_my_cxt_init: symbol not found`；注入后 autogen/configure/make 全绿（2026-09-30 实测）。
