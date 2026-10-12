# open-simh

SIMH 历史计算机模拟器套件（open-simh/simh 官方开源延续版）。

## 版本
- 3.12-3：24 个模拟器（PDP-1/4/7/8/9/11/15、PDP-10、VAX/VAX780、NOVA、
  ECLIPSE、IBM 1401/1620/7094、Interdata 16/32b、UC15、SDS 940、LGP-30、
  H316、XDS Sigma、Altair 8800、GRI-909），纯 C、零三方依赖。

## 使用
```bash
pdp11            # 启动 PDP-11 模拟器，交互式 SCP 命令行
echo "show version" | vax   # 脚本化运行
```
