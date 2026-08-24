// test_package/test.cpp — Consumer test for ETL (Extended Template Library)
// Exercises etl::handle reference-counted smart pointer (R34: substantive API usage).

#include <ETL/handle>
#include <ETL/_handle.h>
#include <cstdio>

// A reference-counted object usable with etl::handle.
// ETL's handle machinery requires ref() / unref() (ETL/_handle.h lines 90/100).
class RefCounted
{
public:
	RefCounted() : ref_count_(0) { }
	virtual ~RefCounted() { }

	virtual void ref() const noexcept { ++ref_count_; }
	virtual void unref() const
	{
		if (--ref_count_ == 0)
			delete this;
	}

private:
	mutable int ref_count_;
};

int main()
{
	// Construct a handle; ctor calls obj->ref() (ref_count_ becomes 1).
	etl::handle<RefCounted> h(new RefCounted());

	// Copy-construct; ctor calls obj->ref() (ref_count_ becomes 2).
	etl::handle<RefCounted> h2(h);

	// Verify both handles point to the same object.
	if (h.get() != h2.get())
	{
		printf("FAIL: handle copy did not share object\n");
		return 1;
	}

	// Release h2; dtor calls obj->unref() (ref_count_ becomes 1).
	h2.reset();

	// h still holds the object (ref_count_ == 1).
	if (!h)
	{
		printf("FAIL: handle reset prematurely\n");
		return 1;
	}

	printf("ETL handle refcount lifecycle test PASSED\n");
	return 0;
}
