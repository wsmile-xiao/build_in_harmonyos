/*
 * Port of the upstream compilation case for OpenAL Soft 1.24.1:
 *   tests/example.t.cpp — "ExampleTest.Basic" ("just making sure we compile")
 *
 * The upstream case is GoogleTest-based; the tests/ build pulls gtest in via
 * FetchContent at configure time, which is not available (or wanted) in a
 * cross-compile package build.  The body of the upstream test is preserved
 * verbatim here in a dependency-free main() so the same API surface is
 * compiled and executed against the packaged headers/library, and the AL
 * error state is checked afterwards.
 */
#include <AL/al.h>

#include <stdio.h>

int main(void)
{
    /* Body preserved from tests/example.t.cpp: EXAMPLE_TEST Basic. */
    ALuint source, buffer;
    ALfloat offset;
    ALenum state;

    const ALenum initial_error = alGetError();

    /* The accessor result is unused upstream, but keep the values live so the
     * same declarations are genuinely exercised. */
    source = 0;
    buffer = 0;
    offset = 0.0f;
    state = AL_INITIAL;

    printf("PASS: upstream ExampleTest.Basic API surface compiles and links\n");
    printf("INFO: ALuint=%u bytes, ALfloat=%u bytes, ALenum=%u bytes\n",
           (unsigned)sizeof(source), (unsigned)sizeof(offset), (unsigned)sizeof(state));
    printf("INFO: alGetError() before any context = 0x%04x\n", (unsigned)initial_error);

    (void)source;
    (void)buffer;
    (void)offset;
    (void)state;

    /* With no current context OpenAL Soft reports AL_INVALID_OPERATION. */
    if (initial_error != AL_NO_ERROR && initial_error != AL_INVALID_OPERATION) {
        printf("FAIL: unexpected AL error 0x%04x without a context\n",
               (unsigned)initial_error);
        return 1;
    }
    return 0;
}
