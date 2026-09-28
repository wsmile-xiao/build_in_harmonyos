# VTK 9.3.0 真机测试报告

## 最终 W3 实测结果

官方 finish 的全新源码构建和制品消费者已通过，退出 0。完整上游 CTest 为
1830 通过、0 失败、2 跳过、0 未执行，分母 1832；JUnit 耗时 178 秒。
三个消费者执行五次，31 项正向断言及两个反向控制通过，预期进程退出码为 0/1/0/1/0。

- 实际 W3 包：`vtk/9.3.0#58fb5a42258706b5ca3573d97ad883ef:5b7b8277201cc2f49e0dda85113c3ab9cc47f49e#c15b1b9167a022395fbf0969a5b4b3c3`。
- W3 日志 SHA256：`93c6aa1c4d757a8023948c31b99275edeeaf4638686e59827f6c83d60220fa95`。
- JUnit SHA256：`23f8a8623db246f71c166b786201148e710ec73643579ed1189d34ecdf3994d1`。
- 原始回传归档 SHA256：`acdab5a87ddf3ba8a45ca9e0b50a0f08777e9d1dd3b26dd1ed9a7d941ba7203a`。
- 机器记录：`native-validation.json`；完整原始归档在任务交付目录 `upstream/recipe-validation32/`。

两项跳过为上游 Windows 专用 AVIWriter/MP4Writer 条件，保留在总分母。
全部条目通过率 99.89%，有通过/失败结果条目的通过率 100%；五次消费者执行均符合预期。
此前 export-pkg 缓存准备与其前置完整套件在机器记录中单列，不充当全新构建。

原始 finish 总退出码为 1：W3 成功后，就绪检查发现报告/打包/暂存标记缺项，
The unchanged E219/E253/E305 entries contain multiline YAML values; the existing checker incorrectly reports them as empty. Their baseline Git blobs are unchanged. The original finish exit 1 is retained; missing task deliverables are completed and checked separately.
