# rtl-wmbus

`rtl-wmbus` is a software-defined receiver for Wireless M-Bus (WM-Bus, EN 13757)
telegrams received by an RTL2832-based DVB-T dongle.

It is a plain C99 command line filter: it reads raw complex-8 (`cu8`) IQ samples
on **stdin** and writes decoded telegrams on **stdout**. The RTL-SDR library is
*not* a build dependency — the `rtl_sdr` capture program is a peer process wired
through a shell pipe:

```sh
rtl_sdr -f 868.95M -s 1600000 - 2>/dev/null | rtl_wmbus
```

Signal chain: FSK demodulation → clock recovery → T1/C1 and S1 packet decoding.

## Versions

| Version | Status |
| --- | --- |
| 1.1.0 | built |

Homepage: https://github.com/wmbusmeters/rtl-wmbus
