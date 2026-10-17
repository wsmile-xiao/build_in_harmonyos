# SWH 0.4.17 adaptation

最终补齐标准 apply_conandata_patches 入口（当前无补丁声明，不改变生成逻辑），
并输出明确的原 bozo 1/1 PASS。r11 原生配方验证和官方本地 CI exit0；上游
1/1、消费者 6/6，12 回执和释放完整。日志 SHA256
d76a1f31c51c65b8761d5eb7ba1b37833c14ddfe1a35458915869e916ba60ef4。
完整 finish 原生 RC1，只有后置 step5b/step8，不宣称整体 PASS 或 worker 发布。

原发行包含 100 XML、96 模块、109 descriptors。完整保留模块和原 Perl
makestub.pl 生成器。原 bozo 校验入口为 1 个，不将 XML 数量当作测试分母。

发布的 Perl 与 XML::Parser XS 加载发生 PL_markstack_ptr 符号不匹配。
用 Python stdlib Expat 构造原 Tree 的有序元素/属性/文本结构，包含 DTD 默认
属性和合并字符数据；以 Perl core JSON::PP 读入，原代码生成逻辑不变。
仅允许发行包内 ladspa-swh.dtd，禁止任意实体或网络加载。

头定义的 waveguide_nl_* 改 static inline，解决 C99 外部定义缺失。
四文件九处直接 FFTW_MEASURE 规划在 OHOS build() 改 ESTIMATE；source()
不读取 settings，遵守 Conan 跨配置源码缓存约束。保留所有变换参数。

r6 FFT 实例化满核，真实失败；r7 依赖下载超时；r8 错误访问 source.settings；
这些记录不升级。r9 原生 conan create RC0、上游 1/1 和消费者 6/6，
96 模块和 109 IDs 完整，原 30 秒 alarm 未放宽。日志 SHA256
e9b3f1e3eac39441d7c47f293b20507607ce0d4be145165513dcc5acdf487843。
本记录不是平台 CI、合并或发布状态；正式 finish 独立收尾。

未测硬件音频设备；ESTIMATE 可能牺牲长期变换的最优性能，不宣称普遍提速。
