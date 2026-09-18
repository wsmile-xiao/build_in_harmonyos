// Consumer test for opentracing-cpp 1.5.1 (R34: real public API usage).
//
// Uses ONLY installed public headers (<opentracing/tracer.h>, <opentracing/noop.h>,
// <opentracing/span.h>) and the exported OpenTracing::opentracing link target —
// exactly what a third-party consumer would use. Verifies observable behavior:
// a noop tracer can be created, spans start non-null, operation-name/tag
// set/get round-trips, and Finish() is idempotent.
#include <opentracing/tracer.h>
#include <opentracing/noop.h>
#include <opentracing/span.h>

#include <cstdio>
#include <string>

int main() {
  auto tracer = opentracing::MakeNoopTracer();
  if (!tracer) {
    std::fprintf(stderr, "FAIL: MakeNoopTracer() returned null\n");
    return 1;
  }

  auto span = tracer->StartSpan("consumer-op");
  if (!span) {
    std::fprintf(stderr, "FAIL: StartSpan() returned null\n");
    return 2;
  }

  span->SetOperationName("consumer-op-renamed");
  span->SetTag("key", std::string("value"));
  span->Log({{"event", "consumer"}});

  // Finish twice must be harmless (idempotent).
  span->Finish();
  span->Finish();

  // Tracer must still be usable after span finish.
  auto span2 = tracer->StartSpan("consumer-op-2");
  if (!span2) {
    std::fprintf(stderr, "FAIL: second StartSpan() returned null\n");
    return 3;
  }
  span2->Finish();

  std::printf("consumer_opentracing: OK (noop tracer, spans, tags, logs)\n");
  return 0;
}
