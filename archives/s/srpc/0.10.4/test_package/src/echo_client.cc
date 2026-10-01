// 消费者测试 —— srpc 客户端：同步 + 异步两条 RPC 路径，断言响应内容
#include <stdio.h>
#include <stdlib.h>
#include <string>

#include "echo.srpc.h"
#include "srpc/rpc_compress.h"
#include "srpc/rpc_types.h"
#include "workflow/WFFacilities.h"

using namespace srpc;

int main(int argc, char *argv[])
{
	int port = (argc > 1) ? atoi(argv[1]) : 14120;
	int failures = 0;

	GOOGLE_PROTOBUF_VERIFY_VERSION;

	// ── 同步调用 ──
	Example::SRPCClient client("127.0.0.1", port);
	EchoRequest req;
	EchoResponse resp;
	RPCSyncContext sync_ctx;

	req.set_message("Hello, srpc!");
	req.set_name("consumer-test");
	client.Echo(&req, &resp, &sync_ctx);

	if (!sync_ctx.success)
	{
		printf("SYNC_FAILED status=%d error=%d errmsg=%s\n",
			   sync_ctx.status_code, sync_ctx.error, sync_ctx.errmsg.c_str());
		failures++;
	}
	else
	{
		printf("SYNC_RESP: %s\n", resp.message().c_str());
		if (resp.message() != "Hi back: Hello, srpc!")
		{
			printf("SYNC_MISMATCH expected=[Hi back: Hello, srpc!]\n");
			failures++;
		}
	}

	// ── 异步调用 ──
	WFFacilities::WaitGroup wait_group(1);
	Example::SRPCClient async_client("127.0.0.1", port);
	EchoRequest async_req;
	std::string async_payload = "async-hello";
	bool async_ok = false;
	std::string async_body;

	async_req.set_message(async_payload);
	async_client.Echo(&async_req, [&](EchoResponse *async_resp, RPCContext *ctx) {
		if (ctx->success())
		{
			async_ok = true;
			async_body = async_resp->message();
		}
		else
			printf("ASYNC_FAILED status=%d error=%d errmsg=%s\n",
				   ctx->get_status_code(), ctx->get_error(), ctx->get_errmsg());
		wait_group.done();
	});
	wait_group.wait();

	if (!async_ok || async_body != "Hi back: " + async_payload)
	{
		printf("ASYNC_MISMATCH ok=%d body=[%s]\n", (int)async_ok, async_body.c_str());
		failures++;
	}
	else
		printf("ASYNC_RESP: %s\n", async_body.c_str());

	// ── 压缩器 API 往返（gzip/zlib 走 zlib，snappy/lz4 走对应三方库）──
	{
		RPCCompressor *compressor = RPCCompressor::get_instance();
		const std::string origin(8192, 'z');
		const int types[3] = {RPCCompressGzip, RPCCompressSnappy, RPCCompressLz4};
		const char *names[3] = {"gzip", "snappy", "lz4"};

		for (int i = 0; i < 3; i++)
		{
			int type = types[i];
			int capacity = compressor->lease_compressed_size(type, origin.size());
			if (capacity <= 0)
			{
				printf("COMPRESS_LEASE_FAILED %s\n", names[i]);
				failures++;
				continue;
			}

			std::string compressed(capacity, '\0');
			int compressed_len = compressor->serialize_to_compressed(
					origin.data(), origin.size(), &compressed[0],
					compressed.size(), type);
			if (compressed_len <= 0)
			{
				printf("COMPRESS_FAILED %s rc=%d\n", names[i], compressed_len);
				failures++;
				continue;
			}

			std::string restored(origin.size(), '\0');
			int restored_len = compressor->parse_from_compressed(
					compressed.data(), compressed_len, &restored[0],
					restored.size(), type);
			if (restored_len != (int)origin.size() || restored != origin)
			{
				printf("COMPRESS_ROUNDTRIP_MISMATCH %s len=%d\n",
					   names[i], restored_len);
				failures++;
			}
			else
				printf("COMPRESS_ROUNDTRIP_OK %s %u->%d\n",
					   names[i], (unsigned)origin.size(), compressed_len);
		}
	}

	if (failures == 0)
		printf("CONSUMER_TEST_OK\n");
	else
		printf("CONSUMER_TEST_FAILED failures=%d\n", failures);

	google::protobuf::ShutdownProtobufLibrary();
	return failures == 0 ? 0 : 1;
}
