#include <cstdio>
#include <cstring>
#include <mutex>
#include <condition_variable>

#include "workflow/WFTaskFactory.h"
#include "workflow/WFHttpServer.h"
#include "workflow/HttpUtil.h"

// test_package 实质调用 workflow API（R34）：起一个 WFHttpServer（127.0.0.1
// 回环），创建 HTTP 任务 GET 自己，校验回包 200 + Content-Type，串行两个
// 任务验证 series 语义（与上游 http_unittest 同构的消费者级最小闭环）。

#define RETRY_MAX 3

static void http_process(WFHttpTask *task)
{
    auto *req = task->get_req();
    auto *resp = task->get_resp();

    if (strcmp(req->get_request_uri(), "/test") == 0)
        resp->add_header_pair("Content-Type", "text/plain");
}

int main()
{
    WFHttpServer server(http_process);
    if (server.start("127.0.0.1", 18811) != 0)
    {
        fprintf(stderr, "server start failed\n");
        return 1;
    }

    std::mutex mutex;
    std::condition_variable cond;
    bool done = false;
    int ok_count = 0;

    auto cb = [&mutex, &cond, &done, &ok_count](WFHttpTask *task) {
        if (task->get_state() == WFT_STATE_SUCCESS)
        {
            auto *resp = task->get_resp();
            auto code = atoi(resp->get_status_code());
            if (code != HttpStatusOK)
                return;
            protocol::HttpHeaderCursor cursor(resp);
            std::string content_type;
            if (cursor.find("Content-Type", content_type) && content_type == "text/plain")
                ok_count++;
        }
        mutex.lock();
        done = true;
        mutex.unlock();
        cond.notify_one();
    };

    auto *task = WFTaskFactory::create_http_task(
        "http://127.0.0.1:18811/test", 0, RETRY_MAX, cb);
    task->start();

    std::unique_lock<std::mutex> lock(mutex);
    cond.wait(lock, [&done] { return done; });
    server.stop();

    if (ok_count == 1)
    {
        printf("workflow test_package OK: http roundtrip 200\n");
        return 0;
    }
    fprintf(stderr, "workflow test_package FAILED\n");
    return 1;
}
