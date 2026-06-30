## 编译信息

- **软件**: netpbm 10.73.42
- **构建系统**: custom-perl (交互式 Perl 配置脚本)
- **编译日期**: 2026-05-22

## 编译方式

由于 netpbm 使用特殊的交互式 Perl 配置脚本，不支持标准 autotools 参数，采用手动创建 config.mk 文件方式配置。

## 制品文件

- `netpbm-10.73.42-ohos-aarch64.tar.gz` (~45MB)
- `netpbm-10.73.42-ohos-aarch64-debug.tar.gz` (~12MB)

## 禁用功能

- 可选图像库支持（PNG/JPEG/TIFF/X11）
- 网络功能（平台限制）

## 测试验证

- 编译成功，生成 357 个图像处理工具
- 静态库 libnetpbm.a 正常生成

## 提交文件

- `archives/n/netpbm/manifest.yaml`
- `archives/n/netpbm/README.md`
- `archives/n/netpbm/10.73.42/manifest.yaml`
- `archives/n/netpbm/10.73.42/notes.md`
- `archives/n/netpbm/10.73.42/packaging/*.tar.gz`

## 参考

- 参考 PR: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/54

---

Co-authored-by: OpenDesk <opendesk@openharmony.cn>