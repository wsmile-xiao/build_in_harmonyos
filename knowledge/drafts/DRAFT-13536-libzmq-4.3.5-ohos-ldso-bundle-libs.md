# DRAFT-13536-libzmq-4.3.5-ohos-ldso-bundle-libs

## OHOS musl ldso 在 LD_LIBRARY_PATH 含 /data/storage/el1/bundle/libs 时中断后续搜索

- **触发场景**：conan create 的 test_package 阶段运行 C++（libc++）测试程序
- **报错签名**：
  ```
  Error loading shared library libc++_shared.so: (needed by <pkg>/p/lib/lib<name>.so)
  Error relocating <pkg>/p/lib/lib<name>.so: _Znwm: symbol not found
  ConanException: Error 127 while executing (test() method)
  ```

### 根因

OHOS PC 默认 shell 与 CI worker 环境的 `LD_LIBRARY_PATH` 末尾带
`/data/storage/el1/bundle/libs/arm64`（应用 bundle 目录，实测约 17 万条目）。
musl ldos 遍历 LD_LIBRARY_PATH 时，走过该巨型目录后**放弃后续所有条目**
（包括 `/system/lib64` 与默认搜索路径），`libc++_shared.so` 遂解析失败。

conan 的 `VirtualRunEnv` 在 test_package 阶段 prepend 包自身 lib 目录并**继承**
进程环境变量，因此在 `conan create` 里稳定复现；手动 shell 里用
`LD_LIBRARY_PATH=<pkg>/lib` 覆盖（不含 el1/bundle）时反而不复现——这也是该坑
容易误判为「conan 环境问题」的原因。

### 复现与验证

```bash
# 复现（el1/bundle 在前）：
LD_LIBRARY_PATH="/data/storage/el1/bundle/libs/arm64:/system/lib64" ./<any_c++_elf>
# → Error loading shared library libc++_shared.so

# 通过（/system/lib64 prepend）：
LD_LIBRARY_PATH="/system/lib64:/data/storage/el1/bundle/libs/arm64" ./<any_c++_elf>
# → 正常运行
```

### 修复方案（推荐）

test_package 的 `test()` 用 conan Environment API 把 `/system/lib64` prepend 到
`LD_LIBRARY_PATH`（不裸用 shell 变量，符合 R33）：

```python
from conan.tools.env import Environment

def test(self):
    env = Environment()
    if self.settings.os == "OHOS":
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
    with env.vars(self).apply():
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"),
                 env="conanrun")
```

### 回退方案

test_package 改链静态库（消费侧 `shared=False` 或包仅提供 static），绕开
`libc++_shared.so` 动态解析。

### 影响面

所有 C++（libc++）动态库包的 test_package（本机 LD_LIBRARY_PATH 含 el1/bundle
条目即踩）。libzmq 4.3.5（任务 #13536）实测：首跑复现签名，加 prepend 后
全部通过。

### 与既有条目的关系

- E077（ELF 签名/RPATH）、E024（AF_UNIX bind）不覆盖本问题——本条是**动态
  链接器搜索路径中断**，属通用平台坑，建议审核后正式收录。
