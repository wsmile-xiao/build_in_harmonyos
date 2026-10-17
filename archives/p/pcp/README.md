# pcp (Performance Co-Pilot)

## 简介
PCP 是 Linux 性能监控/采集套件：pmapi 客户端库 + pmcd/pmlogger 守护进程 +
pmstat/pmval/pmdumplog 等命令行工具 + PMDA 插件体系（linux/linux_proc/pmdaext 等）。
用于实时指标采集、归档（pmlog）与事后分析。

## OHOS 适配
- **构建系统**: autotools（in-tree 构建：PCP 的 C install 忽略 DESTDIR，configure/make/install 全在 source folder 跑，`--prefix=<package_folder>`）
- **最小组件集**: 核心 pmcd/pmlogger/pmstat/pmval + pmapi；`--without-*` 关闭 perl/python3/qt/x/systemd/selinux/infiniband/perfevent 及全部非核心 PMDA
- **关键适配**:
  - OHOS musl libc 缺 glibc/BSD 专属符号（rindex/re_comp/versionsort/HZ/qsort_r）→ 标准等价物移植（31 补丁）
  - `CROSS_COMPILING=yes` 跳过 .static 静态可执行（OHOS 静态 libpthread 缺 pthread_cancel）；make install 前置重查 build 目标，变量须重传（conanfile `_make_override_vars()`）
  - lld `--no-allow-shlib-undefined` 默认：sysroot libc 缺 pthread_cancel/setcancelstate（设备 libc 有）→ 构建期 make 命令内联 LDFLAGS + 消费期 package_info exelinkflags（2026-10-13 本地 AI 检视后由孤儿 env 脚本改为显式内联）
  - install-sh 无条件调 id（OHOS 无 id/chown）→ REAL_UID fallback
  - umask 077→007（hmdfs 组 file_manager 可写）、TMPDIR→$HOME/tmp、PCP_CONF 指向构建树（/etc 只读）
- **/proc 数据源**: OHOS PC 选择性暴露（diskstats root-only、PSI cpu/io 缺失）——linux/linux_proc PMDA 天然按维度降级（指标 unavailable 而非 die()），无需为 /proc 打补丁；详见知识草稿 E1005
- **测试**: 上游 qa 套件（3774 编号测试 + 273 C 程序）多数需 live pmcd，CI 不可运行（B 档受阻申报）；免 context 抽样 2/2 PASS；test_package L1（pmErrStr）1/1

## 版本
- `7.1.5/` — 首次适配（2026-10-09）
