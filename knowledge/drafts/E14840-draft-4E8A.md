# E14840 — Conan 私有 Python 应用依赖的嵌入式运行闭包

状态：草稿。来源：libsigrokdecode/0.5.3，任务 contrib-14840，在 HarmonyOS PC 真机上通过 Conan 2 验证。

## 错误特征

一个共享 C 库嵌入 `libpython`。`conan create` 的上游测试已全绿、包也已安装，但在 `test_package` 图求值时失败：

```text
Skipped binaries: ... python/3.12.9.1 ...
ERROR: libsigrokdecode/0.5.3: Error in package_info() method
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

另一种表现是已链接的库或消费者在运行时找不到 `libpython3.12.so.1.0`。前者是图/元数据问题，后者是运行环境问题；上游测试通过不能代替消费端验证。

## 触发条件和根因

- Conan 的 Python 包为 `application` 类型，但当前 C 库在构建时需要 Python 头、`libpython`，运行时也必须加载解释器和标准库。
- 公开宿主依赖与 Python 的传递依赖存在不同的精确版本（本例 GLib 经 `zlib/1.3.2`，Python 经 `zlib/1.3.1.1`）。盲目把版本统一到任一侧会改变已发布包的 package ID，未必存在对应二进制。
- 当确认嵌入式 Python 的 API/ABI 已封装，使用 `visible=False` 可使两条私有/公开闭包共存；但消费者图会跳过该私有应用二进制。于是 `package_info()` 内该依赖的 `package_folder` 为 `None`，也不能假定消费者能找到 `libpython`。
- `no_skip=True` 仅强制保留二进制，不自动完成 `PYTHONHOME` 和动态库搜索路径的传播。这一点与已有的 pytest 应用依赖草稿一致，不能把 `no_skip` 当作环境修复。

## 可复用修复

1. 先用完整 `conan graph info` 确认冲突版本及所有预编译 package ID；仅当不能选择已发布的统一闭包、且 Python 不暴露在本包公共 ABI 中时，才使用 `self.requires("python/<version>", visible=False, no_skip=True)`。不要默认把所有 Python 依赖私有化。
2. `package_info()` 中在消费者图读取 Python 的实际 `package_folder`，导出 `PYTHONHOME` 和其 `lib` 目录到 `runenv_info`；本包自身的共享库目录也要进入运行路径。路径必须来自本次 Conan 图，不得写死缓存哈希。
3. 在 `build()` 的测试步骤和 `package()` 的安装步骤，凡会执行解释器、Check runner 或生成的 ELF，都显式用 Conan 依赖的现有 `lib` 目录构造 `LD_LIBRARY_PATH`。`Autotools.install()` 可能通过脚本再次调用 Python，不能因 `make check` 通过就省略安装环境。
4. 用真正使用安装包的消费者验证：编译链接本库、初始化解释器、加载一个随包安装的 Python 模块或解码器；同时检查消费者图没有 `Skipped binaries: python`，而不仅是检查构建图。

## 边界与反例

- `visible=False` 仅适用于完全封装的依赖。若公共头、ABI 或消费者链接命令暴露 Python，必须解决版本统一和重新发布所需二进制，不能靠隐藏依赖掩盖冲突。
- `no_skip=True` 不等于 `run=True` 或完整环境传播。若目标依赖的 `runenv_info` 缺失，仍需在当前包声明实际所需路径，并以消费者运行证实。
- 不把 Conan 缓存中的 Python 或 zlib 文件复制进本包，不修改依赖包缓存，也不把未验证的 zlib override 当作已发布二进制。
- `TEMP` 优先于 `P_tmpdir` 的 Check 临时目录问题已有 E571 草稿；旧 `config.sub` 的 OHOS 三元组问题已有 E007/E072/E122/E268。本条新增的是 *私有 application 依赖在消费者图的二进制保留与运行环境双层闭环*，不重复申报这些既有机制。

## 验证证据

- 前一轮 `libsigrokdecode-w3-20261003T141305Z`：上游 39/39、安装通过，但消费者图的 `python.package_folder=None`，12/12 事务回执中准确记录 FAIL 后释放。
- 使用 `no_skip=True` 后，`libsigrokdecode-w3-20261003T142021Z` 的消费图显示 `python/3.12.9.1 ... Cache` 而非 `Skipped binaries`；其后唯一失败是消费者源文件路径，与本机制无关。
- 最终候选 `libsigrokdecode-w3-20261003T150451Z`：许可证元数据校正为 GPL-3.0-or-later 后重新执行，上游 Check 39/39，安装 112 个协议解码器，消费端 1/1 编译并运行通过；冻结日志 SHA-256 `0de24c3b80992b14497fc0f68010701a240b43c54e12f95be7cfd333a2a10cae`，事务验证 `W3_PASS`，12/12 回执，runner 已退出。

## 关联知识

- E007/E072/E122/E268：旧 Autotools 三元组识别。
- `DRAFT-E571-ohos-libcheck-temp-env-first-probe`：Check 0.15.2 的 `TEMP` 优先级。
- `DRAFT-pytest-9.1.1-application-dep-skip`：`no_skip` 保留二进制但不替代环境传播。
