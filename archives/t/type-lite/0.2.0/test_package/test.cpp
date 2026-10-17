// type-lite 0.2.0 — test_package 消费者验证
// 通过 Conan 包消费 nonstd/type.hpp，验证强类型语义（非空壳测试）
#include <cassert>
#include <cstdio>

#include "nonstd/type.hpp"

typedef nonstd::ordered<int, struct order_id_tag, nonstd::no_default_t> OrderId;

int main()
{
    OrderId oid(42);
    assert( nonstd::to_value(oid) == 42 );
    assert( oid == OrderId(42) );
    assert( oid != OrderId(43) );
    assert( oid <  OrderId(50) );
    assert( nonstd::make_hash(oid) == nonstd::make_hash(oid) );

    nonstd::boolean<struct active_tag, nonstd::no_default_t> on(true);
    assert( static_cast<bool>(on) == true );
    assert( static_cast<bool>(!on) == false );

    std::printf("test_package type-lite: ALL PASSED (version %d.%d.%d)\n",
                (int)type_MAJOR, (int)type_MINOR, (int)type_PATCH);
    return 0;
}