# librb

`librb` 是 Michal Lyszczek 编写的环形缓冲（FIFO 队列）C 库，API 贴近 POSIX read/write：
单次调用读写多个元素、多线程阻塞/非阻塞、越限自动扩容（growable）、变长帧（dynamic）、
免 malloc 嵌入模式，以及可直传 POSIX read/write 的 claim/commit 零拷贝接口。整个库仅
`rb.c` + 生成的 `rb.h` 一个编译单元，便于集成。

- 上游仓库：https://github.com/mlyszczek/librb
- 文档站：https://librb.bofc.pl
- 许可证：BSD-2-Clause
- 构建系统：autotools（`make check` 运行 mtest TAP 套件）
- 类型：C 库（产物 librb.so/a，头文件 rb.h）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0.0 | built | 首次适配 HarmonyOS PC (aarch64)，待真机预检回填实测数字 |
