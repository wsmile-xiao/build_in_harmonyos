# kernelshark

Kernel Shark：Linux 内核追踪（ftrace/trace-cmd）数据的前端阅读器。
上游仓库 https://git.kernel.org/pub/scm/utils/trace-cmd/kernel-shark.git

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.4.0 | built | 核心层 libkshark（vendored trace 三库 + json-c）；plot/GUI 层因 freeglut/GLU 缺失未构建 |

## OHOS 适配要点

- 分层交付：libkshark 核心（本次）→ libkshark-plot（需 freeglut+GLU，缺失）→ GUI（Qt6+FreeSans，且依赖 plot）
- libtraceevent/libtracefs/libtracecmd 仓内与制品仓均无 Conan 包：recipe 内 vendored 构建（address-standardizer 先例）
- OHOS btf.h 缺新 BTF kinds、musl 无 qsort_r：vendored trace-btf-compat.h
- 上游 CMake plot 门控缺 GLUT 条件、Qt6 REQUIRED 自相矛盾、安装期 ldconfig：portability 补丁修正
