# DRAFT-libscca-20250915-config-sub-ohos-triplet-top-shortcircuit-verify
> 老旧config.sub不识别OHOS三元组时的顶部短路识别与全树自检验补丁
## 问题特征（真实日志片段/标记）
- 真机conan create在configure报：checking build system type... Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'.
- 紧随：configure: error: /bin/sh .../src/config.sub aarch64-unknown-linux-ohos failed
- 指纹稳定：attempt 37752未解决v2:compile:configure_failed，attempt 37837解决且门禁passed；行号827到869证明上一轮内部锚点补丁已同步仍失败。
## 根因
- libscca-20250915自带2024-01-01版config.sub，配方旧_patch_config_sub第三步锚点os2-emx旧版式在新文件中不存在，新文件为os2-emx-，导致linux-ohos内核校验被静默跳过。
- 2024版内部校验分支多、锚点随版本漂移，逐行打补丁不可靠且失败时静默；与版本无关的顶部短路识别才可靠。
- 已排除Meson替代与编译器缺失：源码包config.guess/config.sub齐全，日志无127错误，早于编译器探测；配方已有_resolve_compilers回退逻辑。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 恢复被截断的archives/l/libscca/20250915/conanfile.py，保持工作树完整。
2. 重写_patch_config_sub：在shebang后插入仅匹配*-linux-ohos/*-ohos-linux的case短路块并回显规范三元组，其余输入原样落回原逻辑，不触动内部版本相关分支。
3. build()改走os.walk对源码树下全部config.sub副本逐一打补丁，避免子目录残留旧副本。
4. 新增_verify_config_sub：用_ohos_shell在真机实执行config.sub aarch64-unknown-linux-ohos自检并记录输出，失败即抛ConanException，静默漏补变loud报错。
5. 本地用Git自带sh实测9组：aarch64-unknown-linux-ohos返回0回显，aarch64-linux-ohos/aarch64-ohos-linux/arm64-linux-ohos正确规范化，x86_64-pc-linux-gnu与--version不受影响；py_compile验证配方语法。
## 禁止策略
- 禁止只补顶层config.sub或只做内部锚点替换而不做全树实执行自检：残留副本仍报Kernel linux not known to work with OS ohos，configure直接退出，门禁v2:compile:configure_failed不通过。
## 与相近条目的边界（查重）
- 顶部短路识别加全树补丁加自检构成跨autotools库可复用的config.sub OHOS三元组通用模式。
- 现有条目均为shebang或tmpdir/umask/awk子目录问题，与本次config.sub版本漂移导致内核校验失败相邻但不相同，不重复，需新增。
- 关键词autotools_configure/config_sub/ohos_triplet标识本模式。
## 适用判断
- 适用：Autotools库自带老旧config.sub，configure需识别OHOS三元组，日志出现Invalid configuration与Kernel linux not known to work with OS ohos。
- 不适用：config.sub已原生支持ohos、非configure校验失败、编译器缺失127错误。
- 验证：真机shell实执行config.sub aarch64-unknown-linux-ohos返回0，preflight全部门禁通过。
