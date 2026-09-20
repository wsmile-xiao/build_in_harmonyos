# E999 — conanfile generate() 中 save_script("conanbuild") 覆盖 Conan 聚合 env 脚本 → 自引用递归 SIGSEGV

## 错误特征

```
knowthelist/2.3.1@ohpcd/stable: RUN: "..."qmake QMAKE_PKG_CONFIG=pkg-config src.pro
knowthelist/2.3.1@ohpcd/stable: ERROR:
Package '...' build failed
ERROR: knowthelist/2.3.1@ohpcd/stable: Error in build() method, line 109
    self.run('...qmake...', ...)
    ConanException: Error -11 while executing
```

或手动复现：

```
$ bash -c '. conanbuild.sh && qmake -query QMAKE_SPEC'
[stderr]
Signal 11 (core dumped)
```

根因：Conan 在 generate 目录写入聚合 env 脚本 `conanbuild.sh`（内含 `. "conanbuild.sh" && . "conanbuildenv-*.sh"`）。若配方 generate() 里再调用 `Environment().vars(self).save_script("conanbuild")`，会把该脚本改写为对自身路径的 `.` 引用 → 无限递归 → 栈溢出 → SIGSEGV（子进程 Signal 11 / Error -11）。

## 推荐方案

不要在 generate() 中 `save_script("conanbuild")`。改为在 build()/package() 里创建
`Environment` 并用 `with env.vars(self).apply():` 包裹 `self.run(...)`（参考
`archives/q/qt5-qtimageformats/5.15.2/conanfile.py`）：

```python
def _build_env(self):
    env = Environment()
    env.prepend_path("PATH", os.path.join(qt.package_folder, "bin"))
    env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)  # R49 私有 prefix
    return env

def build(self):
    with self._build_env().vars(self).apply():
        self.run('"%s" ... src.pro' % qmake, cwd=src_dir)
```

若必须用 save_script，改用非 "conanbuild" 的名字并在 `self.run(..., env="<其他名字>")` 引用。

## 来源

- 事件：knowthelist 2.3.1 qmake 构建 conan create G2 失败
- 修复后 conan-verify 全 8 门禁 PASS
