# kicad-library-footprints 10.0.5 测试报告

> 归档路径：`archives/k/kicad-library-footprints/10.0.5`
>
> 上游：<https://gitlab.com/kicad/libraries/kicad-footprints>，tag `10.0.5`
>
> 源码 SHA-256：`f6305041ea72ab9c55461873dfd67359d28fa9639e7a11952b81d468b2155a8d`

## 1. 上游清点

上游 tar.gz 清点得到 155 个 `.pretty` footprint 库、15,447 个 `.kicad_mod` 文件和 0 个 C/C++ 源文件。顶层 CMake 为 `project(kicad-footprints NONE)`，仅定义安装规则；源码内没有 `tests/`、`enable_testing()`、`add_test()`、CTest 或 pytest 注册。`.gitlab-ci.yml` 只远程 include `kicad-library-utils` 的 footprint CI 配置，相关检查脚本不在本源码归档内。

## 2. 适配后包结果

| 产物 | 实测值 |
| --- | ---: |
| `share/kicad/footprints/*.pretty` | 155 个目录 |
| `share/kicad/footprints/**/*.kicad_mod` | 15,447 个文件 |
| `share/kicad/template/fp-lib-table` | 25,235 字节 |
| `licenses/LICENSE.md` | 2,101 字节 |
| 解压后包体 | 157,989,700 字节 |
| C/C++/可执行产物 | 0 |

上游 CMake 的 `install(DIRECTORY ...)` 和 `install(FILES fp-lib-table ...)` 被真实执行，未自行复制替代构建语义。

## 3. Conan 验证

### 3.1 原生 Conan create

环境为 Conan 2.29.1、Windows x86_64、CMake 3.31.8。命令：

```text
conan create archives/k/kicad-library-footprints/10.0.5 --build=missing
```

结果：构建、安装、打包和 `test_package` 均成功，退出码 0。Conan 日志显示：

```text
Package kicad-library-footprints/10.0.5 created
kicad-library-footprints consumer: 15454/15454 assertions passed
```

### 3.2 HarmonyOS 专用消费者路径

对 Conan 实际生成的包目录再次运行：

```text
python -B test_package/test_kicad_footprints.py PACKAGE_FOLDER --ohos
```

结果：`kicad-library-footprints consumer: 15456/15456 assertions passed`。这两个新增断言验证鸿蒙模式下 `TMPDIR` 已定义且不等于只读 `/tmp`，并实际在该目录创建/清理截断 footprint 负向夹具。

### 3.3 负向验证

以空目录作为 package folder：

```text
kicad-library-footprints consumer: 0/1 assertions passed
exit code: 1
```

测试确实依赖被测包的资源布局；移除资源后不会错误报告成功。

## 4. OHOS profile 与真机边界

项目 OHOS profile 能被本机 Conan 解析为 `os=OHOS`、`os.version=6.0`、`arch=armv8`。由于当前执行主机是 Windows，profile 指向的 `/data/service/hnp/bin/bash` 和 Unix Makefiles 无法执行，OHOS profile 的 `conan create` 在 CMake 配置启动处退出码 1；该结果不能作为 HarmonyOS 构建通过证据。

对用户提供的 `10.53.45.8:8022` 做连接检查，TCP 端口和 ICMP 均超时，未能执行设备端 Conan 或运行测试。报告明确保留该阻塞，不将本机 `--ohos` 消费者分支冒充真机结果。

## 5. 仓库级检查

`python tests/run_all.py` 执行到 12 个套件：11 个套件通过；`test_v1220.py` 在已有的 Linux 绝对 Git 路径 `/data/service/hnp/git.org/git_2.45.2/bin/git` 处触发 Windows `FileNotFoundError`。这属于仓库测试在 Windows 主机上的环境兼容问题，未修改框架文件绕过它。

## 6. 结论

资源包本身已完成并通过真实 Windows Conan create、普通消费者测试、鸿蒙专用消费者路径和负向验证。最终 HarmonyOS 6.0/aarch64 原生构建与真机运行仍需在可达设备或 CI OHOS worker 上执行；当前阻塞条件是设备网络不可达和本机缺少 OHOS SDK shell/toolchain，而非配方测试失败。
