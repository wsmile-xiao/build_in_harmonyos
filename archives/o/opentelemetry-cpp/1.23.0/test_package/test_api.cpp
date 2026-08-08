#include <opentelemetry/trace/provider.h>

int main() {
    auto provider = opentelemetry::trace::Provider::GetTracerProvider();
    if (!provider) return 1;
    auto tracer = provider->GetTracer("harmonyos-test", "1.0");
    return tracer ? 0 : 2;
}
