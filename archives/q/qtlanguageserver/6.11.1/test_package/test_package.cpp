#include <QtLanguageServer/private/qlanguageserverspectypes_p.h>

int main()
{
    using QLspSpecification::TraceValue;
    const TraceValue value = TraceValue::Messages;
    return value == TraceValue::Messages ? 0 : 1;
}
