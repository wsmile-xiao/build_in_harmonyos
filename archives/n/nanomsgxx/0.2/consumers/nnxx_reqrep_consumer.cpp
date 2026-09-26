/*
 * consumers/nnxx_reqrep_consumer.cpp — nanomsgxx 独立消费者用例
 *
 * 模拟业务上层组件，仅通过已安装/导出的公开头文件 <nnxx/*.h> 与公开 API
 * 使用 nanomsgxx，验证第三方 C++ 应用能否编译、链接、调用并正常运行：
 *   nnxx::socket(nnxx::SP, nnxx::REQ) / nnxx::socket(nnxx::SP, nnxx::REP)
 *   s.bind("inproc://...") / s.connect("inproc://...")
 *   s.send(...) / s.recv()   (REQ/REP 请求-应答回环，得到可观察业务结果)
 *
 * API 行为说明：nanomsg REQ socket 在收到应答前不可重复 send（REQ 状态机），
 * REP socket 必须按序 recv → send。因此回环流程为：
 *   rep.bind("inproc://nnxx-consumer"); req.connect("inproc://nnxx-consumer");
 *   req.send("ping?")  ->  rep.recv() == "ping?"
 *   rep.send("pong!")  ->  req.recv() == "pong!"
 *
 * 编译参考：
 *   clang++ consumers/nnxx_reqrep_consumer.cpp \
 *       -I<nnxx-include> -I<nanomsg-include> \
 *       -L<nnxx-lib> -L<nanomsg-lib> -lnnxx -lnanomsg -pthread
 */
#include <nnxx/socket>
#include <nnxx/message>

#include <cstdio>
#include <string>

int main()
{
    /* Step 1 — 创建 REQ / REP 一对 socket（底层调用 nanomsg nn_socket）。 */
    nnxx::socket req(nnxx::SP, nnxx::REQ);
    nnxx::socket rep(nnxx::SP, nnxx::REP);
    if (!req || !rep)
    {
        std::printf("consumer FAIL: 无法创建 REQ/REP socket\n");
        return 1;
    }

    /* Step 2 — REP 绑定、REQ 连接（inproc 进程内传输）。 */
    rep.bind("inproc://nnxx-consumer");
    req.connect("inproc://nnxx-consumer");

    /* Step 3 — 请求-应答回环：req 发送 "ping?"，rep 接收后回 "pong!"。 */
    const std::string ping = "ping?";
    int n = req.send(ping.c_str(), 0);
    if (n < 0)
    {
        std::printf("consumer FAIL: req.send() 返回 %d\n", n);
        return 1;
    }

    nnxx::message m1 = rep.recv();
    if (!m1)
    {
        std::printf("consumer FAIL: rep.recv() 返回空消息\n");
        return 1;
    }
    const std::string got1(static_cast<const char *>(m1.data()), m1.size());
    if (got1 != ping)
    {
        std::printf("consumer FAIL: rep 收到的请求为 '%s'，期望 '%s'\n",
                    got1.c_str(), ping.c_str());
        return 1;
    }

    const std::string pong = "pong!";
    n = rep.send(pong.c_str(), 0);
    if (n < 0)
    {
        std::printf("consumer FAIL: rep.send() 返回 %d\n", n);
        return 1;
    }

    nnxx::message m2 = req.recv();
    if (!m2)
    {
        std::printf("consumer FAIL: req.recv() 返回空消息\n");
        return 1;
    }
    const std::string got2(static_cast<const char *>(m2.data()), m2.size());
    if (got2 != pong)
    {
        std::printf("consumer FAIL: req 收到的应答为 '%s'，期望 '%s'\n",
                    got2.c_str(), pong.c_str());
        return 1;
    }

    std::printf("consumer PASS: REQ/REP 回环 '%s' -> '%s' over inproc://\n",
                got1.c_str(), got2.c_str());
    return 0;
}
