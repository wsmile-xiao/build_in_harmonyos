# DRAFT-libnxt-0.5.2-meson-thin-archive-install-true-ar-repack
> Meson未安装静态库默认thin归档致消费者链接断裂的install:true根治与ar重打兜底
## 问题特征（真实日志片段/标记）
- 主包meson构建成功，test_package链接期ld.lld报错：ld.lld: error: p/lib/libnxt.a: could not get the buffer for a child of the archive: 'libnxt.a.p/cmd.c.o': No such file or directory，随后clang-15报linker command failed，make报Error 1（attempt 62231）。
- 中间纠偏轮meson.configure中断：meson.build:1:0: ERROR: Unknown option: b_thin_archives（attempt 62594前序下发所致）。
- 真机推进验证：62231断裂经install:true路线到62646编译通过并进入后续ctest阶段，证实归档根治有效。
## 根因
- Meson大于等于0.60对未安装静态库默认打thin包，魔数为thin标记，成员为libnxt.a.p下目标文件的相对引用；上游0.5.2 meson.build中static_library缺install:true而两executable有install:true，符合thin archives仅针对uninstalled static libraries的通用行为。
- 配方此前仅拷贝libnxt.a单文件进包，消费者侧对象引用悬空，与源码无关；属构建系统通用行为缺陷，install:true加ar重打方案跨库可复用，非单库个案。
- 虚构内建选项b_thin_archives在Builtin-options表无此项，经tc.project_options下发必报未知选项，与thin根因无关。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 删除虚构下发：archives/l/libnxt/0.5.2/conanfile.py中删除tc.project_options下发b_thin_archives并加注禁设原因，避免meson.configure报Unknown option。
2. 根治：patches/0001-use-prebuilt-flash-driver.patch追加第二hunk，给static_library加install:true，使Meson直接产出完整归档；hunk头新旧行数须等于体部上下文加减行数之和，第二hunk起点随首hunk净增位移，否则conan报extra lines或Failed to parse patch。
3. 兜底：conanfile.py的打包函数以8字节魔数判定thin，命中则收集同级libnxt.a.p下目标文件并用已探测archiver执行ar rcs重打完整包后拷贝到lib/libnxt.a；缺archiver时加非空守卫，保留告警放行。
4. 同步：manifest.yaml去掉相关错误选项并同步知识条目，conandata.yml登记补丁说明，notes.md追加复检记录；真机以conan create全链路验证消费者链接不再断裂。
## 禁止策略
- 禁止经tc.project_options下发b_thin_archives：Meson无此内建选项，必致meson.configure中断并退回补丁修正循环；应以install:true根治加ar重打兜底替代。
## 与相近条目的边界（查重）
- 查重语料5acd1dc中无thin、b_thin_archives、install:true、could not get buffer条目，本条为增量新增。
- 既有命中均为HMBS_PLATFORM_CAPABILITIES样板或相邻异因条目，如静态库传递链接闭包缺符号、链接标志变量引用缺失，其失败在缺符号或缺标志，本条失败在归档成员引用悬空且主包构建成功，不适用彼方案。
## 适用判断
- 适用：Meson配方主包构建成功但消费者ld.lld报could not get the buffer for a child of the archive，且归档头为thin标记、上游static_library缺install:true时。
- 不适用：链接报缺符号缺闭包、缺链接标志、编译器缺失或archiver缺失致generate中断时，应走各自条目；本条不改变上游测试口径。
