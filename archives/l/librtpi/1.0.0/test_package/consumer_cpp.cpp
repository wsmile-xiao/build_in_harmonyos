/* librtpi 1.0.0 C++ binding consumer (Conan test_package, HarmonyOS).
 *
 * Verifies the installed C++ binding headers (rtpi/mutex.hpp) compile and
 * behave per the C++ Mutex named requirement, using only kernel-independent
 * fast paths (uncontended try_lock/unlock and self-deadlock detection):
 *   1 - rtpi::mutex default construction and try_lock()/unlock()
 *   2 - lock()/unlock() round trip
 *   3 - double lock() throws std::system_error with EDEADLK
 *   4 - native_handle() exposes the underlying pi_mutex_t and it works
 */
#include <cerrno>
#include <cstdio>
#include <system_error>

#include <rtpi/mutex.hpp>

static int failures;

#define CHECK(expr)                                                     \
	do {                                                            \
		if (!(expr)) {                                          \
			std::fprintf(stderr, "FAIL: %s at %s:%d\n",     \
				     #expr, __FILE__, __LINE__);        \
			failures++;                                     \
		}                                                       \
	} while (0)

int main()
{
	/* 1: try_lock()/unlock() on a fresh mutex. */
	rtpi::mutex m;
	CHECK(m.try_lock());
	m.unlock();

	/* 2: lock()/unlock() round trip (uncontended: CAS fast path). */
	m.lock();
	m.unlock();

	/* 3: self-deadlock surfaces as std::system_error(EDEADLK). */
	m.lock();
	bool threw = false;
	int code = 0;
	try {
		m.lock();
	} catch (const std::system_error &e) {
		threw = true;
		code = e.code().value();
	}
	CHECK(threw);
	CHECK(code == EDEADLK);
	m.unlock();

	/* 4: native_handle() interoperates with the C API. */
	pi_mutex_t *handle = m.native_handle();
	CHECK(handle != nullptr);
	CHECK(pi_mutex_trylock(handle) == 0);
	CHECK(pi_mutex_unlock(handle) == 0);

	if (failures) {
		std::fprintf(stderr, "consumer_cpp: %d failure(s)\n",
			     failures);
		return 1;
	}
	std::printf("librtpi C++ binding consumer passed\n");
	return 0;
}
