# E327 草稿：将 Conan 构建上下文编译器映射到自定义 HOSTCC/HOSTLD

> **状态**：`draft: true`
> **来源**：cmus 2.12.0，PR #5467，知识库扩展 Issue #2225

## 使用说明

适用于交叉编译中同时存在两类 C/C++ 产物的项目：

1. 最终部署到目标平台的库或程序，由目标 `CC/CXX` 编译；
2. 构建过程中立即运行的代码生成器、文档生成器或探针，由构建机编译器编译。

当上游使用 `HOSTCC/HOSTLD`、`BUILD_CC` 等自定义变量，而 Conan 通过 `CC_FOR_BUILD/CXX_FOR_BUILD` 表达构建上下文时，配方必须显式完成语义映射。

## 错误特征

cmus 2.12.0 的自定义 configure 默认将 `HOSTCC` 设为 `gcc`：

```text
checking for program gcc... no
```

配置在 `check_host_cc` 阶段终止。另一类常见表现是错误地把目标交叉编译器作为 `HOSTCC` 后，构建时工具虽然编译成功，但立即运行时报：

```text
Exec format error
```

## 根因

cmus 的目标对象使用 `CC/LD`，但 `Doc/ttman` 是构建阶段运行的文档生成器：

```make
Doc/ttman.o: Doc/ttman.c
	$(call cmd,hostcc,)

Doc/ttman: Doc/ttman.o
	$(call cmd,hostld,)

%.1: %.txt
	Doc/ttman $< $@
```

上游把构建机编译器命名为 `HOSTCC/HOSTLD`。Conan 2 的 `AutotoolsToolchain` 只有在 build profile 显式配置原生 `tools.build:compiler_executables` 时，才会在交叉构建环境导出 `CC_FOR_BUILD/CXX_FOR_BUILD`；build profile 本身不会安装或凭空生成编译器。两套命名不会被自定义 configure 自动互认。

这与 E095 不同：E095 解决的是自定义 configure 不尊重目标 `CXX`；本问题要求同时保留目标编译器和构建机编译器两个上下文。

## 推荐方案

生成 Conan GNU 构建环境，并在同一个 `env="conanbuild"` 子进程中映射变量：

```python
from conan.tools.gnu import AutotoolsToolchain


def generate(self):
    tc = AutotoolsToolchain(self)
    tc.generate()


def build(self):
    if cross_building(self):
        self.run(
            'test -n "${CC_FOR_BUILD:-}" || '
            '{ echo "CC_FOR_BUILD is required" >&2; exit 1; }',
            env="conanbuild",
        )
        host_compiler = "$CC_FOR_BUILD"
    else:
        host_compiler = "$CC"
    self.run(
        f'./configure LD="$CC" HOSTCC="{host_compiler}" '
        f'HOSTLD="{host_compiler}" ...',
        env="conanbuild",
    )
```

映射规则：

- 真正交叉构建：只使用 build profile 或构建上下文工具明确贡献的 `CC_FOR_BUILD`，缺失则 fail closed；
- 原生构建：使用工具链已定义的 `CC`；
- 目标 `LD` 显式映射为目标 `$CC`，`HOSTLD` 映射为宿主编译器驱动；两者都不使用裸 `ld`，以继承正确的启动文件、默认库和 `-Wl,` 参数解析。

如果 build profile 没有原生编译器，应通过 `tool_requires` 提供构建机工具链，再由其 `buildenv_info` 或 `conf_info` 注入 `CC_FOR_BUILD`，不能无条件复用目标交叉编译器。

## 输入与输出

### 输入

- Conan host profile：目标平台、目标编译器；
- Conan build profile：构建机平台及可执行编译器；
- 上游自定义变量名，如 `HOSTCC/HOSTLD`、`BUILD_CC`。

### 输出

- 目标二进制保持目标架构；
- 构建时工具为构建机可执行架构；
- configure 不再回退探测不存在的 `gcc`；
- 文档或生成源码可以在构建阶段真实生成。

## 验证

```sh
# 识别双编译器模型
grep -R "HOSTCC\|HOSTLD\|CC_FOR_BUILD" configure Makefile scripts

# 构建后核验宿主工具
file Doc/ttman
Doc/ttman Doc/cmus.txt /tmp/cmus.1

# 核验目标产物
file cmus cmus-remote ip/wav.so ip/cue.so

# 使用明确的 host/build profile 复验
conan create . -pr:h=<target-profile> -pr:b=<build-profile>
```

cmus 2.12.0 当前在 OHOS aarch64 原生 build/host 上下文中验证：默认 `gcc` 探测失败修复后，构建日志真实出现 `HOSTCC Doc/ttman.o`、`HOSTLD Doc/ttman` 和三项 `MAN` 生成步骤；目标 cmus 与 WAV/CUE 插件完成构建、签名和加载，消费者断言 7/7 通过。异构交叉分支采用缺少 `CC_FOR_BUILD` 即失败的安全契约，当前任务未声称执行了第二种架构的构建机验证。

## 禁止做法

- 禁止在真正异构交叉构建中无条件设置 `HOSTCC=$CC`；目标程序无法在构建机运行。
- 禁止硬编码 `HOSTCC=gcc`；OHOS 环境没有 GNU gcc，且绕过 Conan build profile。
- 禁止使用裸 `HOSTLD=ld`；链接宿主程序应优先使用宿主编译器驱动。
- 禁止只验证目标产物而不执行构建时生成器；编译成功不代表架构上下文正确。

## 适用范围

该模式适用于 custom Make、Kbuild、非标准 configure 以及任何在交叉编译时构建并立即运行原生生成器的项目。变量名可不同，但判断标准相同：若某个中间 ELF 会在构建阶段执行，它必须来自 build context，而不是 host/target context。
