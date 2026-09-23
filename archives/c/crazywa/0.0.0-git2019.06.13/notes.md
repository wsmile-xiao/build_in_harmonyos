# crazywa 0.0.0-git2019.06.13 适配记录

## 来源与版本

作者官方仓库 https://hgm.nubati.net/git/crazywa.git ，固定提交
`055bf038677d879e2bcccae8b6051f60af16b352`，提交日期 2019-06-13。
程序内部版本为 1.0.5；包版本保留任务指定的日期版本。
GitWeb 旧链接已失效，正式配方直接 clone 作者仓库并 checkout 固定提交。
conandata 的 SHA256 校验对象是该提交的 dropper.c，不是不存在的 tarball。

## W0 / W0b / W1

最新主线 a675263b91fd9cef49cbce7aafb54062ae10df2c 无同名归档，无历史 notes。
源码只使用系统 C/POSIX 头文件，无第三方依赖。制品仓 v2 revisions 查询返回
404 error:not found；Conan 高层查询曾返回策略错误，不将该错误当缺包依据。
工具链为设备 OHOS armv8 clang 15，CMake 封装用于接收 Conan toolchain 设置。

## 源码与构建

官方 git ls-tree -r --name-only HEAD 只有 dropper.c、crazywa.pod、logo.png。
没有 Makefile/CMake/测试目录。新增最小 CMake 构建入口，源码保持原样，无补丁。
原始源码设备 clang -O2 编译成功；既有编译警告如隐式函数声明原样披露，未压制。
可执行文件签名后复制入包，签名后不 strip/改写字节。

## 测试口径与限制

上游测试 N=0，适配后保留的上游测试仍为0，无默认或可选测试入口；不写 100% 上游通过。
新增 12 个 unittest 协议用例：握手、ping、格式错误输入、setboard 黑方行棋走子，
以及 crazyhouse/shogi/minishogi/judkinshogi/torishogi/euroshogi/crazywa/kyotoshogi
八种棋类的深度 1 搜索。构建产物和安装后消费者均执行同一组 12 用例；重复执行
不累计成 24 个独立用例。各 case 中通用超时/退出检查及多个断言不另外计数。
setboard 将初始棋子布局设为黑方行棋，检查输出在20个黑方合法走法中，
能检出忽略 setboard 而仍由白方行棋的错误；八种变体只检查搜索完成和
协议输出格式，不等同于棋力、全部规则或长期对局正确性验证。未实跑图形 GUI。

最初将 e2e5 作为应拒绝输入的测试失败。源码 ParseMove 仅解析编码，未验证
完整走子合法性，通常由 GUI 提供合法走子。改为验证 `usermove invalid` 返回
Illegal move；这是修正测试假设，没有更改上游行为。原失败日志保存在本地 task-data。

## 许可证

上游树没有许可证文件。Debian 维护者记录的作者授权为 GPL v3 or later：
https://metadata.ftp-master.debian.org/changelogs/main/c/crazywa/unstable_copyright 。
随包提供标准 GPLv3 COPYING；文本来自 GNU GCC 官方镜像 COPYING3。
