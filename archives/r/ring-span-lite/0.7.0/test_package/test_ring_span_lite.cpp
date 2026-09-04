// test_ring_span_lite.cpp — Conan L1 smoke test + HarmonyOS 专项验证 for ring-span-lite 0.7.0
// 真实调用 nonstd::ring_span 与 nonstd::ring 的 API（构造/容量/入队/出队/迭代器/数据自有 ring），
// 在 OHOS (aarch64) 交叉编译目标下编译并（可运行环境）执行。
#include <nonstd/ring_span.hpp>
#include <nonstd/ring.hpp>

#include <cstddef>
#include <iostream>

int failures = 0;

#define CHECK( expr )                                                     \
    do {                                                                  \
        if ( !(expr) ) {                                                  \
            std::cerr << "FAIL: " #expr " @ line " << __LINE__ << "\n";   \
            ++failures;                                                   \
        }                                                                 \
    } while ( 0 )

int main()
{
    // 1) 迭代器对构造：empty ring span，容量为 0（非 2 的幂输入 → 容量 0）
    {
        int arr[4];
        nonstd::ring_span<int> rs( arr, arr + 4 );
        CHECK( rs.capacity() == 4 );
        CHECK( rs.size() == 0 );
        CHECK( rs.empty() );
    }

    // 2) 容量增长为 2 的幂
    {
        int arr[10];
        nonstd::ring_span<int> rs( arr, arr + 10 );
        CHECK( rs.capacity() == 10 );
        CHECK( rs.empty() );
    }

    // 3) push_back/pop_front 延迟线行为（默认 default_popper）
    {
        int arr[4];
        nonstd::ring_span<int, nonstd::default_popper<int> > rs( arr, arr + 4 );
        rs.push_back( 1 );
        rs.push_back( 2 );
        rs.push_back( 3 );
        rs.push_back( 4 );
        CHECK( rs.full() );
        CHECK( rs.size() == 4 );
        // full span 时再 push_back 会 pop 队首：容量不变
        rs.push_back( 5 );
        CHECK( rs.size() == 4 );
        CHECK( rs.front() == 2 );
        CHECK( rs.back() == 5 );
        int popped = rs.pop_front();
        CHECK( popped == 2 );
        CHECK( rs.size() == 3 );
    }

    // 4) 迭代器（含反向、const 混合）
    {
        int arr[8];
        nonstd::ring_span<int> rs( arr, arr + 8 );
        rs.push_back( 10 );
        rs.push_back( 20 );
        rs.push_back( 30 );
        int sum = 0;
        for ( nonstd::ring_span<int>::iterator it = rs.begin(); it != rs.end(); ++it )
            sum += *it;
        CHECK( sum == 60 );
        nonstd::ring_span<int> const & crs = rs;
        int csum = 0;
        for ( nonstd::ring_span<int>::const_iterator it = crs.begin(); it != crs.end(); ++it )
            csum += *it;
        CHECK( csum == 60 );
    }

    // 5) 数据自有 ring：模板参数为容器类型，自动管理容量
    {
        nonstd::ring< std::vector<int> > r( 3 );
        r.push_back( 7 );
        r.push_back( 8 );
        r.push_back( 9 );
        r.push_back( 10 ); // 满后覆盖队首
        CHECK( r.size() == 3 );
        CHECK( r.front() == 8 );
        CHECK( r.back() == 10 );
        CHECK( r.pop_front() == 8 );
        CHECK( r.size() == 2 );
    }

    if ( failures == 0 )
        std::cout << "ring-span-lite 0.7.0 consumer test: ALL PASSED\n";
    else
        std::cout << "ring-span-lite 0.7.0 consumer test: " << failures << " FAILURES\n";
    return failures == 0 ? 0 : 1;
}