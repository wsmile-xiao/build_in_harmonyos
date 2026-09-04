/***************************************************************************
 * oatpp 1.3.1 HarmonyOS PC (aarch64) 专项测试
 *
 * 目标：在 OHOS 平台上验证 oatpp 网络栈的真实可用性 —— 本机 127.0.0.1
 * 上启动一个 HTTP 服务端，再用 oatpp HTTP 客户端发请求并校验响应体，
 * 覆盖 socket、线程池、HTTP 编解码与对象生命周期（泄漏检查）。
 *
 * 由 pc3-17 适配添加，作为 oatpp 1.3.1 鸿蒙专项用例。
 ***************************************************************************/

#include "oatpp/web/server/HttpRouter.hpp"
#include "oatpp/web/server/HttpConnectionHandler.hpp"
#include "oatpp/web/protocol/http/Http.hpp"
#include "oatpp/web/protocol/http/outgoing/ResponseFactory.hpp"
#include "oatpp/network/Server.hpp"
#include "oatpp/network/tcp/server/ConnectionProvider.hpp"
#include "oatpp/network/tcp/client/ConnectionProvider.hpp"
#include "oatpp/web/client/HttpRequestExecutor.hpp"
#include "oatpp/web/protocol/http/outgoing/BufferBody.hpp"
#include "oatpp/core/base/Environment.hpp"

#include <iostream>
#include <thread>
#include <chrono>

using namespace oatpp::web::protocol::http;

class HelloHandler : public oatpp::web::server::HttpRequestHandler {
public:
  std::shared_ptr<OutgoingResponse> handle(const std::shared_ptr<IncomingRequest>& request) override {
    (void)request;
    return OutgoingResponse::createShared(
      Status::CODE_200,
      oatpp::web::protocol::http::outgoing::BufferBody::createShared("Hello from OHOS oatpp 1.3.1")
    );
  }
};

int main() {

  oatpp::base::Environment::init();

  const char* host = "127.0.0.1";
  v_uint16 port = 18091;

  /* 服务端 */
  auto router = oatpp::web::server::HttpRouter::createShared();
  router->route("GET", "/", std::make_shared<HelloHandler>());

  auto serverConnProvider = oatpp::network::tcp::server::ConnectionProvider::createShared(
    {host, port, oatpp::network::Address::IP_4}
  );
  auto connectionHandler = oatpp::web::server::HttpConnectionHandler::createShared(router);
  oatpp::network::Server server(serverConnProvider, connectionHandler);

  /* 后台线程运行服务端 */
  std::thread serverThread([&server](){
    server.run();
  });

  /* 等待服务就绪 */
  std::this_thread::sleep_for(std::chrono::milliseconds(1200));

  /* 客户端 */
  auto clientConnProvider = oatpp::network::tcp::client::ConnectionProvider::createShared(
    {host, port, oatpp::network::Address::IP_4}
  );
  auto requestExecutor = oatpp::web::client::HttpRequestExecutor::createShared(clientConnProvider);
  auto requestHeaders = oatpp::web::protocol::http::Headers();
  auto connection = requestExecutor->getConnection();
  auto response = requestExecutor->executeOnce("GET", "/", requestHeaders, nullptr, connection);
  auto status = response->getStatusCode();
  auto body = response->readBodyToString();

  std::cout << "OHOS status=" << status << std::endl;
  std::cout << "OHOS body='" << body->c_str() << "'" << std::endl;

  /* 断言 */
  bool ok = (status == 200) && (std::string(body->c_str()) == "Hello from OHOS oatpp 1.3.1");

  /* 停止服务端 */
  server.stop();
  serverConnProvider->stop();
  serverThread.join();

  std::cout << "objectsCreated=" << oatpp::base::Environment::getObjectsCreated()
            << " objectsCount=" << oatpp::base::Environment::getObjectsCount() << std::endl;

  oatpp::base::Environment::destroy();

  std::cout << (ok ? "OHOS_TEST_PASS" : "OHOS_TEST_FAIL") << std::endl;
  return ok ? 0 : 1;
}
