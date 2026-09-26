#!/bin/sh
set -eu

dosbox_bin=${1:?missing DOSBox executable path}
test -f "$dosbox_bin"

fail() {
    printf '%s\n' "DOSBOX_CONSUMER_FLOW|FAIL|$1" >&2
    exit 1
}

version_output=$("$dosbox_bin" --version 2>&1) || fail version-exec
case "$version_output" in
    *0.82.2*) ;;
    *) fail "unexpected-version:$version_output" ;;
esac
printf '%s\n' 'DOSBOX_CONSUMER_VERSION|0.82.2|PASS'

unset DOSBOX_NATIVEWINDOW_SURFACE_ID
unset DOSBOX_NATIVEWINDOW_WIDTH
unset DOSBOX_NATIVEWINDOW_HEIGHT

if invalid_video_output=$(\
    DOSBOX_CAPABILITY_PROBE=1 \
    DOSBOX_CAPABILITY_VIDEO=1 \
    SDL_VIDEODRIVER=dummy \
    DOSBOX_NATIVEWINDOW_SURFACE_ID=1 \
    DOSBOX_NATIVEWINDOW_WIDTH=0 \
    DOSBOX_NATIVEWINDOW_HEIGHT=480 \
    "$dosbox_bin" --exit 2>&1); then
    fail invalid-nativewindow-accepted
fi
case "$invalid_video_output" in
    *"DOSBOX_CAPABILITY_VIDEO_FAIL invalid NativeWindow surface tuple"*) ;;
    *) fail "invalid-nativewindow-output:$invalid_video_output" ;;
esac

if ! video_output=$(\
    DOSBOX_CAPABILITY_PROBE=1 \
    DOSBOX_CAPABILITY_VIDEO=1 \
    SDL_VIDEODRIVER=nativewindow \
    SDL_RENDER_DRIVER=opengles2 \
    "$dosbox_bin" --set output=texture \
        -c "echo DOSBOX_NATIVEWINDOW_WORKLOAD" \
        -c "choice /T:y,3 /N" --exit 2>&1); then
    fail video-exec
fi
case "$video_output" in
    *"DOSBOX_CAPABILITY_VIDEO_PRESENT|driver=nativewindow|renderer=opengles2|frame_available=1"*) ;;
    *) fail "video-marker:$video_output" ;;
esac
printf '%s\n' 'DOSBOX_CONSUMER_VIDEO|nativewindow|opengles2|frame_available=1|PASS'

if ! audio_output=$(\
    DOSBOX_CAPABILITY_PROBE=1 \
    DOSBOX_CAPABILITY_AUDIO_TONE=1 \
    DOSBOX_CAPABILITY_AUDIO_ONLY=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=ohaudio \
    "$dosbox_bin" -c "echo DOSBOX_OHAUDIO_WORKLOAD" \
        -c "choice /T:y,5 /N" --exit 2>&1); then
    printf '%s\n' "$audio_output" >&2
    fail audio-exec
fi
case "$audio_output" in
    *"DOSBOX_CAPABILITY_AUDIO_ONLY|video=disabled|audio=enabled"*) ;;
    *) fail "audio-only-marker:$audio_output" ;;
esac
case "$audio_output" in
    *"DOSBOX_CAPABILITY_AUDIO_CALLBACK|driver=ohaudio|bytes="*"|nonzero=1"*) ;;
    *) fail "audio-marker:$audio_output" ;;
esac
printf '%s\n' 'DOSBOX_CONSUMER_AUDIO|ohaudio|mixed_nonzero=1|PASS'

tmp_root=${TMPDIR:-.}
dynrec_conf=$(mktemp "$tmp_root/dosbox-capability-dynrec.XXXXXX") || \
    fail dynrec-config-create
trap 'rm -f "$dynrec_conf"' EXIT HUP INT TERM
{
    printf '%s\n' '[cpu]' 'core=dynamic'
} > "$dynrec_conf"
if ! dynrec_output=$(\
    DOSBOX_CAPABILITY_PROBE=1 \
    DOSBOX_CAPABILITY_DYNREC=1 \
    DOSBOX_CAPABILITY_AUDIO_ONLY=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy \
    "$dosbox_bin" --set output=texture \
        --conf "$dynrec_conf" \
        -c "echo DOSBOX_DYNREC_GUEST_SENTINEL" -c "exit" --exit 2>&1); then
    fail dynrec-exec
fi
case "$dynrec_output" in
    *"DOSBOX_CAPABILITY_DYNREC|core="*"|execution=entered"*) ;;
    *) fail "dynrec-core-marker:$dynrec_output" ;;
esac
case "$dynrec_output" in
    *"DOSBOX_CAPABILITY_DYNREC_STAGE|run-code-after"*) ;;
    *) fail "dynrec-guest-execution:$dynrec_output" ;;
esac
case "$dynrec_output" in
    *"DOSBOX_DYNREC_GUEST_SENTINEL"*) ;;
    *) fail "dynrec-guest-sentinel:$dynrec_output" ;;
esac
printf '%s\n' 'DOSBOX_CONSUMER_DYNREC|entry=1|guest_execution=1|PASS'

normal_conf=$(mktemp "$tmp_root/dosbox-capability-normal.XXXXXX") || \
    fail normal-config-create
trap 'rm -f "$dynrec_conf" "$normal_conf"' EXIT HUP INT TERM
{
    printf '%s\n' '[cpu]' 'core=normal'
} > "$normal_conf"
if ! normal_output=$(\
    DOSBOX_CAPABILITY_PROBE=1 \
    DOSBOX_CAPABILITY_DYNREC=1 \
    DOSBOX_CAPABILITY_AUDIO_ONLY=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy \
    "$dosbox_bin" --set output=texture \
        --conf "$normal_conf" \
        -c "echo DOSBOX_NORMAL_GUEST_SENTINEL" -c "exit" --exit 2>&1); then
    fail normal-core-exec
fi
case "$normal_output" in
    *"DOSBOX_CAPABILITY_DYNREC"*) fail normal-core-marker;;
esac

printf '%s\n' 'DOSBOX_CONSUMER_FLOW|4/4|PASS'
