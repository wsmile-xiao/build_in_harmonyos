/*
OHOS / HarmonyOS audio backend for qrq, using the native OHAudio API.

qrq renders the complete CW waveform into a single buffer and then calls
write_audio() once, followed by close_audio().  OHAudio only offers a pull
(callback) model, so this backend keeps the samples pushed by write_audio()
in a buffer and hands them to the OH_AudioRenderer from its write-data
callback.  The renderer is started in close_audio(), which also waits until
all samples were consumed and the hardware buffer had time to drain.

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
Street, Fifth Floor, Boston, MA  02110-1301, USA.

*/

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>

#include <ohaudio/native_audiostreambuilder.h>
#include <ohaudio/native_audiorenderer.h>

extern long samplerate;

/* Maximum time close_audio() waits for the renderer to consume all samples. */
#define QRQ_OHOS_DRAIN_TIMEOUT_S 30

typedef struct {
	OH_AudioStreamBuilder *builder;
	OH_AudioRenderer *renderer;
	short *samples;		/* accumulated mono samples */
	int capacity;		/* allocated samples */
	int count;			/* valid samples */
	int consumed;		/* samples already handed to the renderer */
	pthread_mutex_t lock;
	pthread_cond_t cond;
} ohos_audio_t;


/* Pull callback: the renderer asks for 'audio_data_size' bytes of audio. */
static OH_AudioData_Callback_Result write_cb (OH_AudioRenderer *renderer,
		void *user_data, void *audio_data, int32_t audio_data_size) {
	ohos_audio_t *a = (ohos_audio_t *) user_data;
	short *out = (short *) audio_data;
	int frames = audio_data_size / (int) sizeof(short);
	int avail, n;

	(void) renderer;

	pthread_mutex_lock(&a->lock);
	avail = a->count - a->consumed;
	n = (frames < avail) ? frames : avail;
	if (n > 0) {
		memcpy(out, a->samples + a->consumed, n * sizeof(short));
		a->consumed += n;
	}
	if (n < frames) {
		/* pad with silence once the waveform is exhausted */
		memset(out + n, 0, (frames - n) * sizeof(short));
	}
	if (a->consumed >= a->count) {
		pthread_cond_signal(&a->cond);
	}
	pthread_mutex_unlock(&a->lock);

	return AUDIO_DATA_CALLBACK_RESULT_VALID;
}


void *open_dsp (char *device) {
	ohos_audio_t *a;
	OH_AudioStream_Result res;

	(void) device;		/* OHAudio selects the output device itself */

	a = (ohos_audio_t *) calloc(1, sizeof(*a));
	if (!a) {
		return NULL;
	}
	pthread_mutex_init(&a->lock, NULL);
	pthread_cond_init(&a->cond, NULL);

	res = OH_AudioStreamBuilder_Create(&a->builder, AUDIOSTREAM_TYPE_RENDERER);
	if (res != AUDIOSTREAM_SUCCESS) {
		fprintf(stderr, "OHAudio: OH_AudioStreamBuilder_Create failed: %d\n",
				(int) res);
		goto fail;
	}

	OH_AudioStreamBuilder_SetSamplingRate(a->builder, (int32_t) samplerate);
	OH_AudioStreamBuilder_SetChannelCount(a->builder, 1);
	OH_AudioStreamBuilder_SetSampleFormat(a->builder, AUDIOSTREAM_SAMPLE_S16LE);
	OH_AudioStreamBuilder_SetEncodingType(a->builder, AUDIOSTREAM_ENCODING_TYPE_RAW);
	OH_AudioStreamBuilder_SetLatencyMode(a->builder, AUDIOSTREAM_LATENCY_MODE_NORMAL);
	OH_AudioStreamBuilder_SetRendererInfo(a->builder, AUDIOSTREAM_USAGE_MUSIC);
	OH_AudioStreamBuilder_SetRendererWriteDataCallback(a->builder, write_cb, a);

	res = OH_AudioStreamBuilder_GenerateRenderer(a->builder, &a->renderer);
	if (res != AUDIOSTREAM_SUCCESS) {
		fprintf(stderr, "OHAudio: GenerateRenderer failed: %d\n", (int) res);
		goto fail;
	}

	return a;

fail:
	if (a->builder) {
		OH_AudioStreamBuilder_Destroy(a->builder);
	}
	pthread_mutex_destroy(&a->lock);
	pthread_cond_destroy(&a->cond);
	free(a);
	return NULL;
}


/* Accumulate the samples handed over by qrq (one 32 bit value per sample). */
void write_audio (void *handle, int *in, int size) {
	ohos_audio_t *a = (ohos_audio_t *) handle;
	int frames = size / (int) sizeof(int);
	int i;

	if (!a) {
		return;
	}

	pthread_mutex_lock(&a->lock);
	if (a->count + frames > a->capacity) {
		int cap = a->count + frames + 4096;
		short *tmp = (short *) realloc(a->samples, cap * sizeof(short));
		if (!tmp) {
			pthread_mutex_unlock(&a->lock);
			return;
		}
		a->samples = tmp;
		a->capacity = cap;
	}
	for (i = 0; i < frames; i++) {
		a->samples[a->count++] = (short) in[i];
	}
	pthread_mutex_unlock(&a->lock);
}


/* Start the renderer, play the buffered waveform and release everything. */
void close_audio (void *handle) {
	ohos_audio_t *a = (ohos_audio_t *) handle;
	OH_AudioStream_Result res;
	struct timespec deadline;

	if (!a) {
		return;
	}

	if (a->count > 0) {
		res = OH_AudioRenderer_Start(a->renderer);
		if (res != AUDIOSTREAM_SUCCESS) {
			fprintf(stderr, "OHAudio: OH_AudioRenderer_Start failed: %d\n",
					(int) res);
		}
		else {
			clock_gettime(CLOCK_REALTIME, &deadline);
			deadline.tv_sec += QRQ_OHOS_DRAIN_TIMEOUT_S;

			pthread_mutex_lock(&a->lock);
			while (a->consumed < a->count) {
				if (pthread_cond_timedwait(&a->cond, &a->lock,
							&deadline) == ETIMEDOUT) {
					break;
				}
			}
			pthread_mutex_unlock(&a->lock);

			/* Give the renderer time to drain its internal buffer. */
			usleep(200000);
			OH_AudioRenderer_Stop(a->renderer);
		}
	}

	if (a->renderer) {
		OH_AudioRenderer_Release(a->renderer);
	}
	if (a->builder) {
		OH_AudioStreamBuilder_Destroy(a->builder);
	}
	free(a->samples);
	pthread_mutex_destroy(&a->lock);
	pthread_cond_destroy(&a->cond);
	free(a);
}
