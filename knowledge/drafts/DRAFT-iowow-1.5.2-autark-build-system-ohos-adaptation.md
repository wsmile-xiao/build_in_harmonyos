# DRAFT-iowow-1.5.2-autark-build-system-ohos-adaptation：Autark（build.sh 包装器）构建系统在 OHOS 上的配方适配

> Contributor: pc1-24 | Status: Draft | Updated: 2026-09-21
> Source: iowow 1.5.2 适配（OHOS PC arm64）
> 对应：`knowledge/drafts/DRAFT-iowow-1.5.2-autark-build-system-ohos-adaptation.kv`

## 现象

使用 Autark 自研构建系统（顶层 `build.sh` 内嵌 amalgamated autark.c）的 C 库
（iowow 等 Softmotions 生态库）在 OHOS 上用 Conan 配方适配时，按 autotools
模板生成的 conanfile.py 直接失败，且出现一串环境/参数陷阱：

```console
$ ./build.sh -j4
# usage 帮助直接打印并退出（autark 不认 -j，jobs 参数是 -J）
error: required tool 'install' not found in PATH
# 构建机默认 PATH 没有 /bin（install 在 /bin 下）
$ conan create ...
# package() 只拷 stage/lib/ 时报:
CMake Error: Library 'iowow' not found in package
# Autark 64 位安装产物实际落在 lib64/
```

## 根因

1. **构建系统误判**：init-build 按 URL 猜构建系统，Autark 项目被猜成 autotools，
   模板配方（AutotoolsToolchain/autotools.configure）与真实构建入口完全不符。
2. **参数不兼容**：autark 的并行任务是 `-J<N>`（`-j` 是位置参数以外的未知选项，
   打印 usage 退出）。
3. **PATH 缺 /bin**：构建机默认 PATH 不含 `/bin`，而 autark `system.sh`
   `check_tool install` 硬校验 `install` 工具（在 `/bin`）。
4. **安装目录是 lib64**：Autark 在 64 位目标上把库装到 `--prefix/lib64/`，
   若 Conan `package()` 只从 `lib/` 拷贝，产物缺库，CMakeDeps 报
   `Library 'iowow' not found in package`。

## 方案

conanfile.py 直接调用 `build.sh`（不走 autotools）：

```python
def build(self):
    # R33: 编译器从 Conan conf 读取，不依赖未定义的 shell 变量
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = compilers.get("c", os.environ.get("CC", "clang"))
    env = {"CC": cc, "BUILD_TYPE": "Release"}
    # 确保 /bin 在 PATH（autark 需要 install 工具）
    path = os.environ.get("PATH", "")
    if "/bin" not in path.split(":"):
        os.environ["PATH"] = "/bin:" + path
    stage = os.path.join(self.build_folder, "stage")
    self.run(f"{env_str} ./build.sh --prefix={stage} -J1", cwd=self.source_folder)

def package(self):
    # Autark 64 位产物在 lib64/，32 位在 lib/，两处都兼容
    for libdir in ("lib64", "lib"):
        if os.path.isdir(os.path.join(stage, libdir)):
            copy(self, "libiowow.a", src=os.path.join(stage, libdir), dst=...)
```

验证：conan-verify G2 干净构建 PASS、test_package 消费者用例 1/1 Passed、
上游 78/78 用例通过。

## 适用范围与边界

- 适用：所有顶层 `build.sh` + `.autark/` 探测脚本的 Autark 项目（iowow、
  Softmotions 生态）。
- 反例：`-j` 来自 GNU make 习惯；若项目 Makefile 再包一层 `make -j` 则无此参数问题。
- 相关：`similar_to: E531`（同 OHOS musl 缺 qsort_r 根因，但 E531 是链接期
  shim 补丁方案；本候选是 Autark 探测脚本预期失败 + 库自带 sort_r.h 自动回退，
  无需补丁——探针失败不是构建失败信号）。
