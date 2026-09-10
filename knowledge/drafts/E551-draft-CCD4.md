# E551: Exult OHOS Autotools 的 SDL2 头文件与消费者验证

## 适用场景

Exult 1.12.1 是基于 Autotools 的 C++ 应用，依赖 SDL2，并在安装后提供 `exult`、`expack` 和 `ipack` 三个命令行程序。其 OHOS aarch64 Conan 配方需要同时处理头文件布局、交叉编译 triplet 和消费者验证。

## 现象

典型问题包括：

```text
fatal error: SDL.h: No such file or directory
SDL.h: No such file
command not found: exult
command not found: expack
command not found: ipack
```

如果只执行 `make check`，还可能误以为已经覆盖了上游测试；Exult 1.12.1 实际没有注册 `tests/`、Automake `TESTS` 或 `check_PROGRAMS` 测试用例。

## 根因

1. Conan 的 SDL2 包通常将头文件放在 `include/SDL2/`，而 Exult 源码直接包含 `SDL.h`。仅生成依赖环境而不把 `include/SDL2` 加入编译器搜索路径，会导致配置或编译失败。
2. OHOS aarch64 构建不是普通 Linux native build，Autotools 需要明确使用 `aarch64-linux-ohos` 作为 `--build` 和 `--host` triplet。
3. `make check` 是递归构建系统检查目标，不等同于已注册的单元测试或集成测试。上游没有正式测试时，适配方必须新增真实消费者测试，调用安装后的 API 或可执行文件。

## 推荐方案

在 `generate()` 中使用 Conan 依赖包自身的路径，不使用共享系统目录：

```python
tc.extra_cxxflags.append(
    f"-I{self.dependencies['sdl2'].package_folder}/include/SDL2"
)
if str(self.settings.os) == "OHOS":
    tc.configure_args.extend([
        "--disable-android-apk",
        "--build=aarch64-linux-ohos",
        "--host=aarch64-linux-ohos",
    ])
```

在 `test_package` 中逐项验证安装产物：

```bash
exult --version
expack --help
ipack --help
```

同时检查命令输出，并显式处理工具文档规定的非零退出码；不能用 `|| true` 把失败吞掉，也不能只打印固定字符串。

## 测试边界记录

Exult 1.12.1 的上游注册测试用例数为 0。适配验证应分别记录：

- 上游 `make check`：作为递归构建检查，单独记录，不计为测试用例；
- 适配补充消费者测试：3 个真实断言，覆盖 `exult`、`expack`、`ipack`。

## 验证命令

```bash
conan create archives/e/exult/1.12.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing

bash archives/e/exult/1.12.1/test_package/test.sh
```

## 禁止做法

- 不要使用 `/usr/local` 或其他共享路径注入 SDL2 头文件和库。
- 不要把 `make check` 递归目标写成上游测试用例数量。
- 不要使用只打印字符串的空壳消费者测试。
- 不要用 `|| true` 隐藏命令、测试或权限错误。

## 来源

- 软件：Exult 1.12.1
- 上游仓库：https://github.com/exult/exult
- 关联 PR：#9238
- 关联提交：525106e7ac
