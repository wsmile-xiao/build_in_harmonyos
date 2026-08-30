#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <vector>

#include <foonathan/memory/heap_allocator.hpp>
#include <foonathan/memory/malloc_allocator.hpp>
#include <foonathan/memory/memory_pool.hpp>
#include <foonathan/memory/new_allocator.hpp>
#include <foonathan/memory/std_allocator.hpp>

namespace {

constexpr std::size_t max_alignment = alignof(std::max_align_t);

template <typename Allocator>
bool check_default_allocator(Allocator& allocator)
{
    for (std::size_t size : {std::size_t(0), std::size_t(1), std::size_t(17), std::size_t(64)}) {
        void* memory = allocator.allocate_node(size, 1);
        if (memory == nullptr) {
            std::fprintf(stderr, "allocate_node returned null for size %zu\n", size);
            return false;
        }
        if (reinterpret_cast<std::uintptr_t>(memory) % max_alignment != 0) {
            std::fprintf(stderr, "allocation for size %zu is not max-aligned\n", size);
            allocator.deallocate_node(memory, size, 1);
            return false;
        }
        allocator.deallocate_node(memory, size, 1);
    }
    return true;
}

} // namespace

int main()
{
    foonathan::memory::heap_allocator heap;
    foonathan::memory::malloc_allocator malloc_alloc;
    foonathan::memory::new_allocator new_alloc;
    if (!check_default_allocator(heap) ||
        !check_default_allocator(malloc_alloc) ||
        !check_default_allocator(new_alloc)) {
        return 1;
    }

    foonathan::memory::memory_pool<> pool(sizeof(int), 4096);
    using int_allocator = foonathan::memory::std_allocator<int, decltype(pool)>;
    std::vector<int, int_allocator> values{int_allocator(pool)};
    values.push_back(7);
    values.push_back(11);
    if (values.size() != 2 || values[0] + values[1] != 18) {
        std::fprintf(stderr, "std_allocator vector check failed\n");
        return 1;
    }

    return 0;
}
