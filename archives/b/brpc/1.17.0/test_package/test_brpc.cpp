// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

// test_package 实质调用 brpc API：起一个 brpc::Server 注册 EchoService，
// 再用 brpc::Channel 发起一次 RPC 往返并校验回包内容（R34）。

#include <cstdio>
#include <cstring>

#include <brpc/server.h>
#include <brpc/channel.h>
#include "echo.pb.h"

namespace example {

class EchoServiceImpl : public EchoService {
public:
    EchoServiceImpl() {}
    virtual ~EchoServiceImpl() {}

    virtual void Echo(google::protobuf::RpcController* cntl_base,
                      const EchoRequest* request,
                      EchoResponse* response,
                      google::protobuf::Closure* done) {
        brpc::ClosureGuard done_guard(done);
        (void)cntl_base;
        response->set_message(request->message());
    }
};

}  // namespace example

int main() {
    brpc::Server server;
    example::EchoServiceImpl echo_service;

    if (server.AddService(&echo_service, brpc::SERVER_DOESNT_OWN_SERVICE) != 0) {
        std::fprintf(stderr, "Failed to add EchoService\n");
        return 1;
    }

    // 端口 0 表示由内核自动分配空闲端口
    brpc::ServerOptions options;
    options.idle_timeout_sec = -1;
    if (server.Start(0, &options) != 0) {
        std::fprintf(stderr, "Failed to start server\n");
        return 1;
    }

    brpc::Channel channel;
    brpc::ChannelOptions channel_options;
    channel_options.timeout_ms = 5000;
    channel_options.max_retry = 3;
    if (channel.Init("127.0.0.1", server.listen_address().port,
                     &channel_options) != 0) {
        std::fprintf(stderr, "Failed to init channel\n");
        return 1;
    }

    example::EchoService_Stub stub(&channel);
    brpc::Controller cntl;
    example::EchoRequest request;
    example::EchoResponse response;
    request.set_message("hello brpc on harmonyos");

    stub.Echo(&cntl, &request, &response, NULL);
    if (cntl.Failed()) {
        std::fprintf(stderr, "RPC failed: %s\n", cntl.ErrorText().c_str());
        return 1;
    }

    if (response.message() != request.message()) {
        std::fprintf(stderr,
                     "RPC response mismatch: got '%s' expected '%s'\n",
                     response.message().c_str(), request.message().c_str());
        return 1;
    }

    std::printf("brpc RPC roundtrip OK: %s\n", response.message().c_str());
    server.Stop(0);
    server.Join();
    return 0;
}
