# ploticus 脚本 — L1 消费者测试用的自包含样例
#
# 覆盖两个鸿蒙相关的关键面：
#   1. proc drawcommands（内联命令）：上游会把这些命令写入
#      $TDH_tmpdir/ploXXXXXX 临时文件；鸿蒙 PC 上 /tmp 为只读挂载，适配补丁
#      0001-src-preliminaries.c.patch 负责在 $TMPDIR / 编译期默认 / 当前目录中
#      选出真正可写的目录。
#   2. proc getdata + proc areadef + proc lineplot：PNG / SVG 实际出图。
#
#proc page
pagesize: 4 3

#proc getdata
data: 1 2
	2 5
	3 4
	4 8

#proc areadef
rectangle: 1 1 4 3
xrange: 0 5
yrange: 0 10

#proc drawcommands
commands:
  color blue
  mov 1 1
  lin 3 2

#proc lineplot
xfield: 1
yfield: 2
linedetails: color=red width=0.5
