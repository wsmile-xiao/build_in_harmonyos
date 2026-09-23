# dicom3tools

DICOM 医学影像离线工具集，David A. Clunie 开发维护。

- 官网：<https://www.dclunie.com/dicom3tools.html>
- 许可证：BSD-3-Clause（见 `COPYRIGHT`）

## 本包内容

102 个 ELF 程序 + 19 个 `#!/bin/sh` 脚本 + 1 个上游自带的 0 字节脚本（`himrunid`），
共 122 个文件安装在 `bin/`；130 个 man 手册安装在
`share/man/man1`。

常用工具：

| 工具 | 用途 |
| --- | --- |
| `dcdump` | 转储 DICOM 文件内容 |
| `dciodvfy` | 按 DICOM IOD/模块规则校验文件 |
| `dccreate` | 从命令行创建 DICOM 文件 |
| `dccp` | 复制并替换属性 |
| `dckey` / `dcdict` | 数据字典查询 |
| `dcstats` | 统计数据集 |
| `dcdirdmp` / `dcdirmk` | DICOMDIR 转储与构建 |
| `dcmulti` | 多帧文件拆分 |
| `dctopnm` / `dctopgx` / `dctoraw` | 像素数据导出 |
| `pnmtodc` / `pgxtodc` / `rawtodc` | 像素数据导入 |
| `dcdisp` | X11 图像显示（需要显示服务） |

## 使用

```sh
conan install --requires=dicom3tools/1.00-20240118131615
# 或从源码构建（版本由配方声明，无需 --version）
conan create . \
    -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
    -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
```

包内为纯可执行程序；`package_info()` 只导出 `bindirs = ["bin"]`。

## 构建

构建走上游的 X11 **imake** 流程（`./Configure` → `imake` → `make`）。
`imake`/`makedepend`/`mkdirhier` 由配方现场从上游指定的官方归档编译，仅作构建工具。
适配细节、补丁说明与验证结果见 `notes.md` 与版本级 `manifest.yaml`。

## 平台

已在 OHOS（aarch64，clang 15 / libc++）构建并验证。依赖 `libx11` 与 `libxext`
（`dcdisp` 及显示相关内部库使用）。

## 已知限制

- 上游测试夹具 `images/` 与 `test/` 由上游单独分发，而该归档在官方站点上不存在
  （任何日期均 404），因此上游测试的 308 个驱动调用点全部无法执行
  （取证见 `reports/upstream-test-evidence.md` 与 `reports/upstream-test-probe.md`）。
- `dcdisp` 需要 X11 显示服务；无显示服务时可正常构建与链接，但不能交互使用。
