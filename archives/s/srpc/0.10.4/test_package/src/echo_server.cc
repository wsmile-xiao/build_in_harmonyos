// 消费者测试 —— srpc 服务端（上层业务视角使用 srpc 公开 API）
#include <signal.h>
#include <stdio.h>
#include <string>

#include "echo.srpc.h"
#include "srpc/rpc_types.h"
#include "workflow/WFFacilities.h"

using namespace srpc;

static WFFacilities::WaitGroup wait_group(1);

class ExampleServiceImpl : public Example::Service
{
public:
	void Echo(EchoRequest *req, EchoResponse *resp, RPCContext *ctx) override
	{
		resp->set_message("Hi back: " + req->message());
		printf("server received: %s\n", req->message().c_str());
		fflush(stdout);
	}
};

static void sig_handler(int signo)
{
	wait_group.done();
}

int main(int argc, char *argv[])
{
	int port = (argc > 1) ? atoi(argv[1]) : 14120;

	GOOGLE_PROTOBUF_VERIFY_VERSION;
	signal(SIGINT, sig_handler);
	signal(SIGTERM, sig_handler);

	SRPCServer server;
	ExampleServiceImpl impl;

	server.add_service(&impl);
	if (server.start(port) != 0)
	{
		perror("server start");
		return 1;
	}

	printf("SERVER_READY port=%d\n", port);
	fflush(stdout);

	wait_group.wait();
	server.stop();
	google::protobuf::ShutdownProtobufLibrary();
	return 0;
}
