# awscli 2.34.56 适配笔记

## 编译环境
- 构建系统: python（conan create，python-require）
- 编译日期: 2026-08-27
- 编译器: 无 C 编译器（纯 Python 项目）
- 状态: built

## 编译步骤

纯 Python 项目，`conan create` 流程：
1. `export_sources()` 内 `export_conandata_patches(self)` 导出 4 个守护补丁
   （必须在 export_sources() 而非 export()——conan 2.29 的 export() 阶段
   export_sources_folder 未设置会抛 TypeError）。
2. `source()` 用 conandata.yml sources 下载官方 GitHub tag 2.34.56 tarball
   （CI 重写为 gh-proxy 镜像 file://）。
3. `build()` 首行 `apply_conandata_patches(self)` 应用补丁；copytree 到
   `self.build_folder/awscli-stage`（round 3 起，WR-008），ignore_patterns 排除
   `.changes/.github/.git/tests/docker/requirements*/backends/bin` 等
   （注意：禁用 `configure*` 之类会误伤 `awscli/customizations/configure/` 的模式）。
4. `package()` 拷 `awscli/` 到 `lib/python3.12/site-packages/`，生成 `bin/aws`
   入口（shebang + sys.path 注入 + `from awscli.clidriver import main`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `aws --version` 无法启动 | vendored botocore 顶层无条件 `import awscrt`（credentials.py:30/utils.py:42/httpchecksum.py:28），clidriver 顶层 `import distro` | 0001/0002/0003/0004 守护补丁 try/except ImportError + 使用处明确降级报错 |
| 2 | 打包缺 `aws configure` | round-1 ignore_patterns 的 `configure*` 误排除 `awscli/customizations/configure/` | 移除该模式（round-2 修复） |
| 3 | conan export 阶段 TypeError | `export_conandata_patches` 放 export()，export_sources_folder 未设置 | 移到 export_sources()（round-2 修复） |
| 4 | round-1 误判 docutils 未发布 | `conan search docutils`（无版本号）Conan 2.x 误报 Recipe not found | web-review 只读核验 + 本轮 conan download 实测确认 0.23 已发布且兼容，round 3 声明入 requires |
| 5 | `aws help` 渲染失败 | ①docutils 缺失（round 2 守护）→ 已解决；②groff/mandoc 管道：OHOS Python subprocess 不解析裸命令名（F5），`Popen(['groff',…])` 抛 FileNotFoundError | round 3 在 help.py 对渲染管道做受控报错守护 |

## 源码修改
`patches/0001~0004`（守护补丁，逐 hunk 中文注释，见 patches/ 目录）。

## 依赖版本
- Python 3.12.9（平台提供，ohpcd python/3.12.9）
- 声明依赖：colorama/0.4.6、ruamel-yaml/0.19.1、ruamel-yaml-clib/0.2.15、
  jmespath/1.1.0、python-dateutil/2.9.0.post0、urllib3/2.7.0、six/1.17.0、docutils/0.23
- 未声明（ohpcd 未发布）：distro、awscrt==0.32.2、prompt-toolkit、wcwidth

## 验证结果

```bash
$ aws --version
aws-cli/2.34.56 Python/3.12.9 HarmonyOS/HongMeng Kernel 1.12.0 source/aarch64

$ aws sts help
aws: [ERROR]: aws help rendering requires the groff/mandoc pipeline, which is not available on this platform
```

## 交付物
- 软件级：`archives/a/awscli/{commands.json, manifest.yaml, README.md}`
- 版本级：`archives/a/awscli/2.34.56/{conanfile.py, conandata.yml, manifest.yaml,
  README.md, notes.md, patches×4, test_package×3}`
