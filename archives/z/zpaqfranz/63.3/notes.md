# zpaqfranz 63.3 HarmonyOS 前置适配

- Issue：待补；仓库及适配建议汇总未检索到明确编号。
- 上游 tag：`fcorbelli/zpaqfranz` 63.3；源码 SHA256 已记录于 conandata.yml。
- 构建系统：`NONWINDOWS/Makefile`，生成单一 CLI `zpaqfranz`；没有 `make check`，但上游提供 `AUTOTEST/README.txt` 定义的内部互操作自测。
- 依赖：无 Conan 依赖；Makefile 使用 C++11、`-pthread`、`-lm`。
- 本轮为本机前置适配，未占用真机窗口。
- 上游真机测试：`zpaqfranz autotest -to <directory>` 报告 `OK 16 ERROR 0`，生成 `sha256.zpaq` 的 SHA256 为 `D90223FAEE2878D7854B9438864B4856A3C1F920C34EFB8C136A8949B54E5400`，与 README 期望一致。后续 `x ... -to ...` 受 zpaqfranz 固定使用 `/tmp/_zpaqfranz` 且该真机路径不可写影响，未将该部分计入 16 项通过率。
- Conan 单包真机验证：L0/L1/L2/L4/L5 全部通过，run 目录见 PR 正文。
- OHOS 修复：补丁仅按 `STATX_BTIME` 能力宏守卫 birth-time 探测，不注入平台条件宏；构建从源码根目录调用 `NONWINDOWS/Makefile`。
