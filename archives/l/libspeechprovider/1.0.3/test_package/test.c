#include <speech-provider.h>

#include <fcntl.h>
#include <string.h>
#include <unistd.h>

static void make_nonblocking_pipe(int fds[2])
{
    g_assert_cmpint(pipe(fds), ==, 0);
    g_assert_cmpint(fcntl(fds[0], F_SETFL, O_NONBLOCK), ==, 0);
    g_assert_cmpint(fcntl(fds[1], F_SETFL, O_NONBLOCK), ==, 0);
}

static void test_bad_header(void)
{
    int fds[2];
    make_nonblocking_pipe(fds);
    SpeechProviderStreamReader *reader = speech_provider_stream_reader_new(fds[0]);
    g_assert_nonnull(reader);
    g_assert_cmpint(write(fds[1], "boop", 4), ==, 4);
    g_assert_false(speech_provider_stream_reader_get_stream_header(reader));
    speech_provider_stream_reader_close(reader);
    close(fds[1]);
    g_object_unref(reader);
}

static void test_round_trip(void)
{
    int fds[2];
    guint8 payload[] = {'f', 'o', 'o'};
    guint8 *audio = NULL;
    guint32 audio_size = 0;
    SpeechProviderEventType event = SPEECH_PROVIDER_EVENT_TYPE_NONE;
    guint32 start = 0, end = 0;
    char *mark = NULL;

    make_nonblocking_pipe(fds);
    SpeechProviderStreamReader *reader = speech_provider_stream_reader_new(fds[0]);
    SpeechProviderStreamWriter *writer = speech_provider_stream_writer_new(fds[1]);
    g_assert_nonnull(reader);
    g_assert_nonnull(writer);

    speech_provider_stream_writer_send_stream_header(writer);
    speech_provider_stream_writer_send_audio(writer, payload, sizeof(payload));
    speech_provider_stream_writer_send_event(
        writer, SPEECH_PROVIDER_EVENT_TYPE_SENTENCE, 20, 24, "bar");

    g_assert_true(speech_provider_stream_reader_get_stream_header(reader));
    g_assert_false(speech_provider_stream_reader_get_event(
        reader, &event, &start, &end, &mark));
    g_assert_cmpint(event, ==, SPEECH_PROVIDER_EVENT_TYPE_NONE);
    g_assert_cmpuint(start, ==, 0);
    g_assert_cmpuint(end, ==, 0);
    g_assert_null(mark);
    g_assert_true(speech_provider_stream_reader_get_audio(reader, &audio, &audio_size));
    g_assert_cmpuint(audio_size, ==, sizeof(payload));
    g_assert_cmpint(memcmp(audio, payload, sizeof(payload)), ==, 0);
    g_free(audio);
    audio = NULL;
    g_assert_false(speech_provider_stream_reader_get_audio(reader, &audio, &audio_size));
    g_assert_cmpuint(audio_size, ==, 0);
    g_assert_true(speech_provider_stream_reader_get_event(
        reader, &event, &start, &end, &mark));
    g_assert_cmpint(event, ==, SPEECH_PROVIDER_EVENT_TYPE_SENTENCE);
    g_assert_cmpuint(start, ==, 20);
    g_assert_cmpuint(end, ==, 24);
    g_assert_cmpstr(mark, ==, "bar");

    g_free(mark);
    speech_provider_stream_reader_close(reader);
    speech_provider_stream_writer_close(writer);
    g_object_unref(reader);
    g_object_unref(writer);
}

int main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/speechprovider/bad-header", test_bad_header);
    g_test_add_func("/speechprovider/round-trip", test_round_trip);
    return g_test_run();
}
