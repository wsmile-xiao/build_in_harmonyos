# visam

V-ISAM — GnuCOBOL 使用的 ISAM（Indexed Sequential Access Method）文件处理器，
同时是 IBM C-ISAM 的替代实现。库本体提供 `isopen`/`isbuild`/`isread`/`iswrite`
等 C-ISAM 兼容接口与十进制转换接口（`vdecimal.h`），并附带
`vcheck`、`vrecover` 两个命令行工具。

- Upstream: http://inglenet.com/gnucobol.html （发布归档 `visam-2.2.tar.Z`）
- 上游镜像/同源项目: https://sourceforge.net/projects/vbisam （README 中标注的历史项目地址）
- Version: 2.2
- Current package: `archives/v/visam/2.2`
- Supported OpenHarmony architecture: armv8（aarch64）
- 构建形态: 静态库 `libvisam.a`（`--disable-shared --enable-static`）

## OpenHarmony 适配要点

1. **autotools 三元组**：上游 `build_aux/config.sub`（timestamp 2020-05-04）不认识
   `ohos`，`cat > build_aux/config.guess`（2020-04-26）在设备上也无法识别 HarmonyOS。
   补丁 `0001`/`0002` 分别补上系统识别与 `linux-ohos` 三元组。
2. **ecvt(3)**：`libvisam/isdecimal.c` 依赖 glibc 扩展 `ecvt()`，OHOS 的 musl libc
   不提供。配方自带 `ohos-ecvt-shim.[ch]` 兼容垫片（不修改上游源码），
   并把目标文件并入 `libvisam.a` 使静态库自包含。
3. **构建为静态库**：OpenHarmony 当前不允许普通可执行文件通过 `DT_NEEDED`
   加载自建的共享库（实测：连新编的最小 `libfoo.so.1` 也无法加载），
   故与仓库主流一致采用静态库。
