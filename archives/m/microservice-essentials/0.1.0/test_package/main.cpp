// HarmonyOS (OHOS) 专项消费者用例 — microservice-essentials 0.1.0
//
// 本用例模拟一个真实的业务上层组件（microservice 内部模块）：
//   - 仅通过本库已安装/导出的公开头文件与公开 API 使用该三方库；
//   - 覆盖 RequestProcessor + RetryRequestHook 的重试语义、Context 元数据
//     传递、Status/StatusCode 转换等有业务意义的公开 API，并输出可观察结果。
//
// 与上游 Catch2 测试（tests/）分开计数：这是消费者视角的独立可执行用例。
#include <chrono>
#include <iostream>
#include <memory>
#include <string>

#include <microservice-essentials/context.h>
#include <microservice-essentials/request/request-processor.h>
#include <microservice-essentials/request/request-type.h>
#include <microservice-essentials/reliability/retry-request-hook.h>
#include <microservice-essentials/status.h>
#include <microservice-essentials/utilities/status-converter.h>

using namespace std::chrono_literals;

int main()
{
  int failures = 0;

  // ---- 1. Status 公开 API：构造 + 布尔判断 + 字符串互转 ----
  mse::Status status_ok;
  if (!static_cast<bool>(status_ok) || status_ok.code != mse::StatusCode::ok)
  {
    std::cerr << "FAIL: default Status should be ok" << std::endl;
    ++failures;
  }
  else
  {
    std::cout << "PASS: default Status is ok" << std::endl;
  }

  mse::Status status_err{mse::StatusCode::unavailable, "backend down"};
  if (static_cast<bool>(status_err))
  {
    std::cerr << "FAIL: explicit error Status should be falsy" << std::endl;
    ++failures;
  }
  else
  {
    std::cout << "PASS: error Status is falsy (" << status_err.details << ")" << std::endl;
  }

  const std::string ok_str = mse::to_string(mse::StatusCode::ok);
  const std::string unimplemented_str = mse::to_string(mse::StatusCode::unimplemented);
  if (ok_str != "OK" || unimplemented_str != "UNIMPLEMENTED")
  {
    std::cerr << "FAIL: to_string conversion mismatch" << std::endl;
    ++failures;
  }
  else
  {
    std::cout << "PASS: StatusCode to_string roundtrip (" << ok_str << "/" << unimplemented_str << ")" << std::endl;
  }

  // ---- 2. StatusCode -> HTTP 状态码转换（公开 API，status-converter）----
  const int http_429 = mse::ToHttpStatusCode(mse::StatusCode::resource_exhausted);
  if (http_429 != 429)
  {
    std::cerr << "FAIL: resource_exhausted should map to 429, got " << http_429 << std::endl;
    ++failures;
  }
  else
  {
    std::cout << "PASS: resource_exhausted -> HTTP " << http_429 << std::endl;
  }

  // ---- 3. RequestProcessor + RetryRequestHook：模拟业务调用 + 重试语义 ----
  // 业务上层组件通过公开 API 构造请求处理器，挂载重试钩子，只依赖公开头文件。
  auto backoff = std::make_shared<mse::LinearRetryBackoff>(2u, 50ms);
  mse::RetryRequestHook::Parameters retry_params(backoff,
                                                 {mse::StatusCode::unavailable});

  mse::Context ctx{{{"consumer-module", "test-consumer"}}, nullptr};
  ctx.Insert("trace-id", "ohpc-0001");
  if (!ctx.Contains("trace-id"))
  {
    std::cerr << "FAIL: Context.Insert/Contains failed" << std::endl;
    ++failures;
  }
  else
  {
    std::cout << "PASS: Context metadata inserted (trace-id="
              << ctx.GetMetadata().find("trace-id")->second << ")" << std::endl;
  }

  mse::RequestProcessor processor("consumer-request", mse::RequestType::incoming, std::move(ctx));
  processor.With(retry_params);

  int attempt = 0;
  const mse::Status final_status = processor.Process([&attempt](mse::Context&) {
    ++attempt;
    if (attempt < 2)
    {
      return mse::Status{mse::StatusCode::unavailable, "transient"};
    }
    return mse::Status::OK;
  });

  if (!static_cast<bool>(final_status) || attempt != 2)
  {
    std::cerr << "FAIL: expected retry then ok, got attempts=" << attempt
              << " status=" << static_cast<bool>(final_status) << std::endl;
    ++failures;
  }
  else
  {
    std::cout << "PASS: RetryRequestHook retried " << attempt - 1
              << "x and request finally succeeded" << std::endl;
  }

  if (failures == 0)
  {
    std::cout << "ALL CONSUMER CHECKS PASSED" << std::endl;
    return 0;
  }
  std::cerr << failures << " consumer check(s) FAILED" << std::endl;
  return 1;
}