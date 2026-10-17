# kicad-demos 10.0.4 适配笔记

## 上游与产物

- 使用 KiCad 官方 10.0.4 源码归档（GitHub `KiCad/kicad` tag 10.0.4），
  demos 目录随主仓分发（原 gitlab `kicad/demo-repositories/kicad-demos`
  独立仓库已下线，404 实证；KiCad 官方 GitLab group 与 GitHub 镜像均确认
  demos 内容在主仓 `demos/` 目录维护）。
- 18 个官方演示工程（711 文件）：cm5_minima、complex_hierarchy、ecc83、
  interf_u、jetson-agx-thor-baseboard、kit-dev-coldfire-xilinx_5213、
  microwave、multichannel、openair-max、pic_programmer、python_scripts_examples、
  royalblue54L_feather、simulation、sonde xilinx、stickhub、tiny_tapeout、
  video、vme-wren。
- 许可证：KiCad 主仓 GPLv3。

## OHOS 适配

纯数据/资源包，无编译无链接。上游 `demos/CMakeLists.txt` 只有一条
`install(DIRECTORY ... DESTINATION ${KICAD_DEMOS})`。配方在 `build()`
阶段核对 18 个工程目录与逐目录文件计数（总量 711），防止下载内容或
目录结构静默漂移；`package()` 将整个 demos 树安装到
`share/kicad/demos/`，并通过 `cpp_info.resdirs` 暴露，
`runenv_info` 定义 `KICAD_DEMOS_DIR`。

## 上游数据勘误（实报）

`royalblue54L_feather/RoyalBlue54L-Feather.kicad_pcb` 存在 KiCad 9
teardrops 块生成器缺陷：`(curved_edges no)filter_ratio 0.9)`——
`filter_ratio` 原子写在闭合括号之外（缺少 `(`），全文件累计 349 个
层外多余闭合括号。KiCad 官方解析器按宽容语义跳过层外多余闭合，官方
demo 按原样分发。本包不修补该文件（保持与官方 tag 逐字节一致），
消费者探针采用与 KiCad 相同的宽容口径（详见测试节）。

## 测试口径

上游 demos 目录不含测试套件（CMakeLists 仅 install 指令），上游测试
N/A。适配后的消费者测试（test_package/kicad_demo_probe.cpp）：

1. 18 个官方演示工程目录在位校验；
2. 全量 s-expression 头解析：19 个 .kicad_pcb + 115 个 .kicad_sch 逐个
   断言根符号（kicad_pcb/kicad_sch）、数字 version 戳、generator 字段，
   并做字符串感知的全文件括号深度扫描（与 KiCad 官方解析器同款宽容
   语义：层外多余 `)` 跳过，未闭合 `(`/字符串报错）；
3. 36 个 .kicad_pro 的 JSON 结构校验（括号/字符串配平 + board/schematic
   配置节存在）；
4. 负向故障注入：截断的 .kicad_pcb 必须被解析器拒绝。

文件计数勘误：shell `find | wc -l` 因 "sonde xilinx.kicad_sch" 带空格
文件名分词漏计（114→实际 115），精确计数以 Python os.walk 为准：
sch=115、pro=36、mod=326、总文件 711。

## 状态

- 本机（HarmonyOS PC aarch64 真机）探针直跑：19 + 115 + 36 全量解析
  通过，截断注入负向 1/1 拒绝，2.6s 完成。
- conan create（ohos-aarch64 交叉 profile）验证见 test-report。
