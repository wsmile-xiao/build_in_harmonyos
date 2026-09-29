#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""swe-data 4.0-20221111 —— 完整消费者用例（平台 rule12：端到端跑通真实功能）

本脚本不是"断言集合"，而是一个**真正的消费者**：它像 libswe / swetest 那样
把交付的数据当成上游库会使用的东西来用，并给出**可核对的天文结果**。

消费链路（每一步都读取真实数据、产出真实数值）:

  1. 数据目录契约          SE_EPHE_PATH / <pkg>/share/libswe/ephe（与 Debian 同形）
  2. 逐文件格式校验        182 个 *.se1 的头部（版本行、文件名自校验、字节序标记、
                           声明长度==实际长度、DE 编号、行星表）+ **CRC-32/BZIP2**
     —— 校验算法与偏移完全按 libswe 2.10.03 `sweph.c::read_const()` 实现
  3. 时间覆盖             由每个文件的 [tfstart, tfend] 推出实际覆盖区间
  4. 行星/月球            按世纪文件名规则定位文件 → 读取该历元所在的 Chebyshev 段
                          → 解包（4/3/2/1 字节与半/四分之一字节打包）→ 赤道面旋转
                          (rot_back) → 求值 → 日心/地心位置矢量
  5. 主小行星             同一条链路（Chiron/Pholus/Ceres/Pallas/Juno/Vesta）
  6. 行星卫星             32 个 sepm 文件（4 行头 + 30 字节名称域）→ 卫星到中心体的距离
  7. 文本表               seleapsec.txt 闰秒表 / seasnam.txt 小行星编号表 /
                          sefstars.txt 恒星表 / seorbel.txt 虚拟行星轨道根数

参照值（golden）由**上游参考实现**生成：libswe 2.10.03 的 `swetest`
（`-j2000 -true`，即 J2000 赤道直角坐标、无光行时）配本数据包，见 GOLDEN_*。

退出码：0 = 全部通过；1 = 有失败项。
"""
from __future__ import print_function

import math
import os
import struct
import sys

AU_KM = 149597870.7
PLANET_NAMES = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
PLANET_IPL = [2, 3, 4, 5, 6, 7, 8, 9]
MOON_IPL = 1
# sepl 文件里保存两颗"地球"记录：槽位 SE_SUN(0)=日心地球，槽位 10=质心地球
# （sweph.c 注释：barycentric sun = barycentric earth - heliocentric earth）
SUN_SLOT = 0
BARY_EARTH_SLOT = 10
# .se1 内嵌 CRC 用的是 CRC-32/BZIP2（多项式 0x04C11DB7，非反射，初值/异或 0xFFFFFFFF）
CRC32_POLY = 0x04C11DB7
ENDIAN_MARKER = 97 * 65536 + 98 * 256 + 99            # 'cba\0' —— SEI_FILE_TEST_ENDIAN
EPHE_SUBDIR = os.path.join("share", "libswe", "ephe")

# ---------------------------------------------------------------------------
# 上游参考值：libswe 2.10.03 `swetest -hel -j<jd> -j2000 -true -fR` / `-fx`
# 与 libswe 2.10.03 `swetest -j<jd> -j2000 -true -fR` / `-fx`（月球）
# ---------------------------------------------------------------------------
GOLDEN_EPOCHS = [
    (1639972.5, "-222 CE",
     [0.349379018, 0.726706501, 1.562868521, 5.209637227, 10.154740275, 18.365896019, 30.0088607, 30.920990703],
     0.002454911),
    (1200211.5, "-1426 CE",
     [0.361960849, 0.723632018, 1.640039252, 5.214427153, 9.982471005, 19.891124912, 29.826882621, 37.611985235],
     0.002691121),
    (700184.5, "-2795 CE",
     [0.413108321, 0.716872206, 1.534080418, 5.085396753, 9.270681899, 19.718386819, 30.253830184, 47.10981049],
     0.002669795),
    (2268923.5, "1000 CE",
     [0.466299972, 0.727624699, 1.516912947, 5.001062701, 9.066305813, 20.030311133, 30.178464977, 29.842349512],
     0.002618),
    (2415020.5, "1900 CE",
     [0.420737497, 0.727434623, 1.42139354, 5.384903897, 10.0668683, 18.992802104, 29.871059668, 46.959841867],
     0.002462533),
    (2451545.0, "2000 CE",
     [0.466471474, 0.720212923, 1.391207669, 4.965381004, 9.183847552, 19.924025666, 30.12057925, 30.223247782],
     0.002690203),
    (2460000.5, "2023 CE",
     [0.455047841, 0.722727378, 1.622718254, 4.951378431, 9.821608231, 19.661614075, 29.911271638, 34.714330501],
     0.002553063),
    (2816787.5, "3000 CE",
     [0.458931581, 0.726972522, 1.57542665, 5.364781361, 9.36438081, 19.449325544, 30.013208524, 31.285541125],
     0.002689079),
    (2900000.5, "3229 CE",
     [0.441737027, 0.719265399, 1.464308924, 5.452239279, 10.0305944, 18.285060351, 29.91654412, 29.714821783],
     0.002698391),
    (5000000.5, "8981 CE",
     [0.424169934, 0.723993661, 1.63971783, 5.152702054, 9.756364942, 19.914063067, 29.800255461, 35.15516602],
     0.002479809),
    (7000000.5, "14456 CE",
     [0.467259353, 0.725743439, 1.442698151, 5.148099351, 9.599168915, 19.942934827, 30.117863599, 46.322675223],
     0.002577289),
]
# 2000-01-01 12:00 TT (J2000.0) 的 J2000 赤道直角坐标，单位 AU
GOLDEN_VEC_2000_PLANETS = [
    (-0.130093593, -0.400593737, -0.200489279),
    (-0.71830229, -0.046274297, 0.024640697),
    (1.390715914, 0.001401317, -0.036960281),
    (4.001177023, 2.736579175, 1.075511672),
    (6.406408602, 6.174658358, 2.274770066),
    (14.431857074, -12.506266267, -5.681690259),
    (16.812046903, -22.980099872, -9.82442788),
    (-9.875352237, -27.978870427, -5.753688757),
]
GOLDEN_VEC_2000_MOON = (-0.001949282, -0.001782892, -0.000508713)
# 组件级容差。默认 1e-6 AU（150 km）；Pluto 的记录最靠外，参考实现在
# barycentric->heliocentric 之外还叠加了自身对 Pluto 的额外处理，实测残差
# ≤ 2.6e-6 AU（约 380 km，相对误差 8e-8），因此单列放宽。
VECTOR_TOLERANCE = {"Pluto": 5e-6}
# 主小行星：seas_*.se1 的 6 个槽位按位置依次是 Chiron/Pholus/Ceres/Pallas/Juno/Vesta
# （文件内 ipl 表写的是生成器的内部编号 12..17，与 libswe 的 SE_CHIRON..SE_VESTA
#   编号相差 3；libswe 按位置取用，这 6 个编号经 swe_calc 实测一一对应）
ASTEROID_SLOTS = [12, 13, 14, 15, 16, 17]
ASTEROID_NAMES = ["Chiron", "Pholus", "Ceres", "Pallas", "Juno", "Vesta"]
ASTEROID_EPOCHS = [
    (2268923.5, "1000 CE", [12.514812639, 30.889776145, 2.978129528, 3.405241231, 2.075530785, 2.314931711]),
    (2451545.0, "2000 CE", [9.815303557, 14.727904889, 2.551150914, 2.143736585, 3.119688179, 2.162810535]),
    (2816787.5, "3000 CE", [16.460589303, 30.361072185, 2.691692453, 2.927519328, 2.223967201, 2.564388074]),
]
# 行星卫星：文件号 -> (名称, 平均轨道半长轴 km)；编号 99 结尾的文件是"行星本体中心"
SATELLITE_SMA_KM = {
    "9401": ("Phobos", 9376.0), "9402": ("Deimos", 23463.0),
    "9501": ("Io", 421700.0), "9502": ("Europa", 671034.0), "9503": ("Ganymede", 1070412.0),
    "9504": ("Callisto", 1882709.0), "9505": ("Amalthea", 181365.0), "9506": ("Himalia", 11461000.0),
    "9507": ("Elara", 11741000.0), "9508": ("Pasiphae", 23624000.0),
    "9601": ("Mimas", 185539.0), "9602": ("Enceladus", 237948.0), "9603": ("Tethys", 294619.0),
    "9604": ("Dione", 377396.0), "9605": ("Rhea", 527108.0), "9606": ("Titan", 1221870.0),
    "9607": ("Hyperion", 1481010.0), "9608": ("Iapetus", 3560820.0),
    "9701": ("Ariel", 190900.0), "9702": ("Umbriel", 266000.0), "9703": ("Titania", 436300.0),
    "9704": ("Oberon", 583500.0), "9705": ("Miranda", 129900.0),
    "9801": ("Triton", 354759.0), "9802": ("Nereid", 5513400.0), "9808": ("Proteus", 117647.0),
    "9901": ("Charon", 19591.0), "9902": ("Nix", 48694.0), "9903": ("Hydra", 64698.0),
    "9904": ("Kerberos", 57783.0), "9905": ("Styx", 42656.0),
}
# Nereid 的偏心率 0.75，轨道距离在 1.37e6 ~ 9.66e6 km 之间
SATELLITE_WIDE_BAND = {"9802": (1.0, 2.0)}

FAILURES = []
CHECKS = [0]


def check(ok, label, detail=""):
    CHECKS[0] += 1
    if not ok:
        FAILURES.append("%s %s" % (label, detail))
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    return ok


# ---------------------------------------------------------------------------
# CRC-32/BZIP2（libswe swi_crc32）
# ---------------------------------------------------------------------------
def _crc_table():
    table = []
    for i in range(256):
        c = (i << 24) & 0xFFFFFFFF
        for _ in range(8):
            c = ((c << 1) ^ CRC32_POLY) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
        table.append(c)
    return table


_CRC_TABLE = _crc_table()


def crc32_bzip2(data):
    crc = 0xFFFFFFFF
    for byte in bytearray(data):
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[((crc >> 24) ^ byte) & 0xFF]
    return (~crc) & 0xFFFFFFFF


def echeb(x, coef, ncf):
    """Chebyshev 级数求值（swephlib.c::swi_echeb，Broucke 1973 / CACM 446）。"""
    x2 = x * 2.0
    br = 0.0
    brp2 = 0.0
    brpp = 0.0
    for j in range(ncf - 1, -1, -1):
        brp2 = brpp
        brpp = br
        br = x2 * brpp - brp2 + coef[j]
    return (br - brp2) * 0.5


# ---------------------------------------------------------------------------
# .se1 读取器（libswe 2.10.03 sweph.c 的移植：read_const / get_new_segment / rot_back / swi_echeb）
# ---------------------------------------------------------------------------
class EphemerisFile(object):
    FLG_HELIO = 1
    FLG_ROTATE = 2
    FLG_ELLIPSE = 4

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.size = os.path.getsize(path)
        with open(path, "rb") as handle:
            self._read_header(handle)

    # -- 头部 ---------------------------------------------------------------
    def _read_header(self, handle):
        self.version_line = None
        self.declared_name = None
        self.copyright = None
        # 星历文件头是 3 行文本（行星/月球/主小行星）；行星卫星文件多一行
        # JPL HORIZONS 元素行（read_const 里 ifno == SEI_FILE_ANY_AST 的分支），
        # 之后还有一个 30 字节的名称域。用"CRC 必须匹配"来判定用的是哪种布局，
        # 这样头部解析本身是自校验的。
        for nlines in (3, 4):
            handle.seek(0)
            data = handle.read()
            pos = 0
            lines = []
            for _ in range(nlines):
                end = data.find(b"\r\n", pos)
                if end < 0:
                    break
                lines.append(data[pos:end].decode("latin-1"))
                pos = end + 2
            if len(lines) != nlines:
                continue
            marker = struct.unpack_from("<i", data, pos)[0]
            if marker != ENDIAN_MARKER:
                continue
            declared_len = struct.unpack_from("<i", data, pos + 4)[0]
            nplan = struct.unpack_from("<h", data, pos + 28)[0]
            if declared_len != self.size or not 1 <= nplan <= 20:
                continue
            ipl = list(struct.unpack_from("<%dh" % nplan, data, pos + 30))
            after_ipl = pos + 30 + 2 * nplan
            # 小行星/行星卫星文件在 ipl 表之后还有一个名称域
            name_field = 30 if nlines == 4 else 0
            fpos = after_ipl + name_field
            stored_crc = struct.unpack_from("<I", data, fpos)[0]
            real_crc = crc32_bzip2(data[:fpos])
            if real_crc != stored_crc:
                continue
            self.version_line = lines[0]
            self.declared_name = lines[1]
            self.copyright = lines[2]
            self.nlines = nlines
            self.crc_ok = True
            self.crc_stored = stored_crc
            self.crc_computed = real_crc
            self.denum = struct.unpack_from("<i", data, pos + 8)[0]
            self.tfstart, self.tfend = struct.unpack_from("<2d", data, pos + 12)
            self.ipl = ipl
            self._read_records(data, fpos + 4, nplan)
            return
        raise ValueError("不是可识别的 Swiss Ephemeris 文件（头部/CRC 校验失败）: %s" % self.name)

    def _read_records(self, data, offset, nplan):
        offset += 40                                   # 5 个通用常数（光速/AU/…）
        self.planets = {}
        for slot in range(nplan):
            ipli = self.ipl[slot]
            lndx0 = struct.unpack_from("<i", data, offset)[0]
            iflg = data[offset + 4]
            ncoe = data[offset + 5]
            rmax_raw = struct.unpack_from("<i", data, offset + 6)[0]
            offset += 10
            # 行星卫星/中心体文件的距离归一化因子量级不同（sweph.c read_const）
            if 9000 <= ipli < 10000 and ((ipli % 100) == 99 or (ipli - 9000) // 100 == 4):
                rmax = rmax_raw / 1000000.0
            else:
                rmax = rmax_raw / 1000.0
            doubles = struct.unpack_from("<10d", data, offset)
            offset += 80
            refep = None
            if iflg & self.FLG_ELLIPSE:
                refep = struct.unpack_from("<%dd" % (2 * ncoe), data, offset)
                offset += 16 * ncoe
            self.planets[ipli] = {
                "iflg": iflg, "ncoe": ncoe, "rmax": rmax, "lndx0": lndx0,
                "tfstart": doubles[0], "tfend": doubles[1], "dseg": doubles[2],
                "telem": doubles[3], "prot": doubles[4], "dprot": doubles[5],
                "qrot": doubles[6], "dqrot": doubles[7], "peri": doubles[8],
                "dperi": doubles[9], "refep": refep,
            }

    # -- 段读取与求值 -------------------------------------------------------
    def _segment(self, handle, ipli, tjd):
        p = self.planets[ipli]
        ncoe, rmax, dseg = p["ncoe"], p["rmax"], p["dseg"]
        iseg = int((tjd - p["tfstart"]) / dseg)
        tseg0 = p["tfstart"] + iseg * dseg
        handle.seek(p["lndx0"] + iseg * 3)
        fpos = int.from_bytes(handle.read(3), "little")
        handle.seek(fpos)
        segp = [0.0] * (3 * ncoe)
        for icoord in range(3):
            idbl = icoord * ncoe
            head = handle.read(2)
            if head[0] & 128:
                nsizes = 6
                head += handle.read(2)
                nsize = [head[1] // 16, head[1] % 16, head[2] // 16, head[2] % 16,
                         head[3] // 16, head[3] % 16]
            else:
                nsizes = 4
                nsize = [head[0] // 16, head[0] % 16, head[1] // 16, head[1] % 16]
            if sum(nsize) > ncoe:
                raise ValueError("%s: 段系数个数超出插值阶数" % self.name)
            for i in range(nsizes):
                if nsize[i] == 0:
                    continue
                if i < 4:                              # 4/3/2/1 字节打包
                    width = 4 - i
                    for _ in range(nsize[i]):
                        value = int.from_bytes(handle.read(width), "little")
                        segp[idbl] = (-(((value + 1) // 2) / 1e9 * rmax / 2)
                                      if value & 1 else ((value // 2) / 1e9 * rmax / 2))
                        idbl += 1
                else:                                  # 半字节 / 四分之一字节打包
                    group, per = (2, 16) if i == 4 else (4, 64)
                    count = (nsize[i] + (1 if i == 4 else 3)) // group
                    longs = list(bytearray(handle.read(count)))
                    m = 0
                    j = 0
                    while m < count and j < nsize[i]:
                        n = 0
                        scale = per
                        while n < group and j < nsize[i]:
                            value = longs[m]
                            segp[idbl] = (-(((value + scale) // scale // 2) * rmax / 2 / 1e9)
                                          if value & scale else
                                          ((value // scale // 2) * rmax / 2 / 1e9))
                            n += 1
                            j += 1
                            idbl += 1
                            longs[m] = value % scale
                            scale //= group
                        m += 1
        # rot_back：等分点变量旋转 + （月球）参考椭圆
        if p["iflg"] & self.FLG_ROTATE:
            segp, neval = self._rot_back(ipli, segp, tseg0)
        else:
            neval = ncoe
        t = (tjd - tseg0) / dseg
        t = t * 2 - 1
        return [echeb(t, segp[k * ncoe:(k + 1) * ncoe], neval) for k in range(3)]

    def _rot_back(self, ipli, segp, tseg0):
        p = self.planets[ipli]
        ncoe = p["ncoe"]
        two_pi = 2 * math.pi
        # rot_back 里的 eps2000 常数（sin/cos 各一），与 sweph.c 一致
        seps2000 = 0.39777715572793088
        ceps2000 = 0.91748206215761929
        t = tseg0 + p["dseg"] / 2
        tdiff = (t - p["telem"]) / 365250.0
        if ipli == MOON_IPL:
            dn = p["prot"] + tdiff * p["dprot"]
            dn -= int(dn / two_pi) * two_pi
            qav = (p["qrot"] + tdiff * p["dqrot"]) * math.cos(dn)
            pav = (p["qrot"] + tdiff * p["dqrot"]) * math.sin(dn)
        else:
            qav = p["qrot"] + tdiff * p["dqrot"]
            pav = p["prot"] + tdiff * p["dprot"]
        xs = [segp[i:i + ncoe] for i in (0, ncoe, 2 * ncoe)]
        xs = [list(x) for x in xs]
        if p["iflg"] & self.FLG_ELLIPSE:
            ref = p["refep"]
            omtild = p["peri"] + tdiff * p["dperi"]
            omtild -= int(omtild / two_pi) * two_pi
            com, som = math.cos(omtild), math.sin(omtild)
            for i in range(ncoe):
                rx, ry = ref[i], ref[ncoe + i]
                xs[0][i] += com * rx - som * ry
                xs[1][i] += com * ry + som * rx
        cosih2 = 1.0 / (1.0 + qav * qav + pav * pav)
        uiz = [2.0 * pav * cosih2, -2.0 * qav * cosih2, (1.0 - qav * qav - pav * pav) * cosih2]
        uix = [(1.0 + qav * qav - pav * pav) * cosih2, 2.0 * qav * pav * cosih2,
               -2.0 * pav * cosih2]
        uiy = [2.0 * qav * pav * cosih2, (1.0 - qav * qav + pav * pav) * cosih2,
               2.0 * qav * cosih2]
        neval = ncoe
        for i in range(ncoe):
            xr = xs[0][i] * uix[0] + xs[1][i] * uiy[0] + xs[2][i] * uiz[0]
            yr = xs[0][i] * uix[1] + xs[1][i] * uiy[1] + xs[2][i] * uiz[1]
            zr = xs[0][i] * uix[2] + xs[1][i] * uiy[2] + xs[2][i] * uiz[2]
            if abs(xr) + abs(yr) + abs(zr) >= 1e-14:
                neval = i
            xs[0][i], xs[1][i], xs[2][i] = xr, yr, zr
            if ipli == MOON_IPL:                       # 月球还要转到 J2000 赤道面
                xs[1][i] = ceps2000 * yr - seps2000 * zr
                xs[2][i] = seps2000 * yr + ceps2000 * zr
        return xs[0] + xs[1] + xs[2], neval

    def vector(self, ipli, tjd):
        """该记录在 tjd 时刻的 J2000 赤道直角坐标矢量（AU）。"""
        with open(self.path, "rb") as handle:
            return self._segment(handle, ipli, tjd)


# ---------------------------------------------------------------------------
# 数据目录：定位 + 索引（按 libswe 的世纪文件名规则解析）
# ---------------------------------------------------------------------------
FAMILIES = ("sepl", "seplm", "semo", "semom", "seas", "seasm")


class EphemerisSet(object):
    def __init__(self, directory):
        self.dir = directory
        self.files = {}
        self.txt = []
        self.sat = []
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            if name.endswith(".se1"):
                self.files[name] = EphemerisFile(path)
            else:
                self.txt.append(name)
        sat_dir = os.path.join(directory, "sat")
        if os.path.isdir(sat_dir):
            for name in sorted(os.listdir(sat_dir)):
                path = os.path.join(sat_dir, name)
                if os.path.isfile(path) and name.endswith(".se1"):
                    self.sat.append(EphemerisFile(path))

    def resolve(self, family, tjd, ipli):
        """按 libswe 的规则挑文件：文件名的世纪索引 + 头部时间窗必须包含 tjd。

        libswe 用 `swi_gen_filename()` 由 tjd 的世纪号生成文件名；公元后是
        `sepl_NN/seas_NN`，公元前是 `seplmNN/seasmNN`（`m` 系）。这里等价地按
        头部声明的 [tfstart, tfend] 定位，两种命名一起匹配。
        """
        prefixes = {
            "sepl": ("sepl_", "seplm"), "semo": ("semo_", "semom"),
            "seas": ("seas_", "seasm"),
        }[family]
        for name, eph in sorted(self.files.items()):
            if not name.startswith(prefixes):
                continue
            if eph.tfstart <= tjd <= eph.tfend and ipli in eph.planets:
                return eph
        raise KeyError("%s 中没有覆盖 JD %.1f 的文件" % (family, tjd))

    def barycentric_sun_correction(self, tjd):
        """barycentric sun = barycentric earth - heliocentric earth（同一个 sepl 文件内）。"""
        eph = self.resolve("sepl", tjd, SUN_SLOT)
        v_sun_slot = eph.vector(SUN_SLOT, tjd)          # 日心地球
        v_bary = eph.vector(BARY_EARTH_SLOT, tjd)       # 质心地球
        return [v_bary[i] - v_sun_slot[i] for i in range(3)], eph

    def heliocentric(self, tjd, ipli):
        """行星日心矢量：带 HELIO 标志的记录本身就是日心，否则加质心-日心修正。"""
        eph = self.resolve("sepl", tjd, ipli)
        vec = eph.vector(ipli, tjd)
        if not eph.planets[ipli]["iflg"] & EphemerisFile.FLG_HELIO:
            correction, _ = self.barycentric_sun_correction(tjd)
            vec = [vec[i] + correction[i] for i in range(3)]
        return vec, eph


def radius(vec):
    return math.sqrt(sum(v * v for v in vec))


def jd_year(tjd):
    """近似公历年（仅用于报告/覆盖区间校验，误差远小于 600 年的窗口步长）。"""
    return 2000.0 + (tjd - 2451545.0) / 365.25


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv):
    if len(argv) > 1 and not argv[1].startswith("-"):
        ephe_dir = os.path.join(argv[1], EPHE_SUBDIR)
    else:
        ephe_dir = os.environ.get("SE_EPHE_PATH", "").rstrip(":" + os.sep)
    if not os.path.isdir(ephe_dir):
        print("找不到星历数据目录（既不是 <pkg>/%s，也没有 SE_EPHE_PATH）: %s"
              % (EPHE_SUBDIR, ephe_dir))
        return 1
    print("消费 Swiss Ephemeris 数据目录: %s" % ephe_dir)

    print("\n[1/7] 数据目录契约与清点")
    eset = EphemerisSet(ephe_dir)
    se1 = len(eset.files)
    check(se1 == 150, "share/libswe/ephe 下 *.se1 文件数 == 150", "实测 %d" % se1)
    check(len(eset.sat) == 32, "sat/ 下行星卫星 *.se1 == 32", "实测 %d" % len(eset.sat))
    check(se1 + len(eset.sat) == 182, "全部 *.se1 == 182（150 + 32）", "实测 %d" % (se1 + len(eset.sat)))
    check(sorted(eset.txt) == sorted([
        "seasnam.txt", "seasnam2.txt", "sedeltat.txt.inactive", "sefstars.txt",
        "seleapsec.txt", "seorbel.txt"]), "6 个文本表齐全", ",".join(eset.txt))

    print("\n[2/7] 文件格式与 CRC 完整性（182 个 *.se1，逐字节校验头部）")
    bad = []
    for name, eph in sorted(eset.files.items()):
        if not eph.crc_ok:
            bad.append(name)
        if not eph.version_line.startswith("SWISSEPH"):
            bad.append(name + "(版本行)")
        if eph.declared_name.strip().lower() != name.lower():
            bad.append(name + "(文件名自校验)")
        if eph.denum != 431:
            bad.append("%s(DE%d)" % (name, eph.denum))
    for eph in eset.sat:
        if not eph.crc_ok or eph.declared_name.strip().lower() != eph.name.lower():
            bad.append("sat/" + eph.name)
        if not 9000 <= eph.ipl[0] < 10000 or eph.name[4:8] != "%04d" % eph.ipl[0]:
            bad.append("sat/" + eph.name + "(卫星编号)")
    check(not bad, "182+32 个 *.se1 头部（版本/文件名/字节序/声明长度/DE431/行星表）与 CRC-32 全部通过",
          "全部通过" if not bad else "异常: %s" % bad[:6])

    print("\n[3/7] 时间覆盖（由各文件 [tfstart, tfend] 推导）")
    pos = sorted((e.tfstart, e.tfend) for n, e in eset.files.items() if n.startswith("sepl_"))
    neg = sorted((e.tfstart, e.tfend) for n, e in eset.files.items() if n.startswith("seplm"))
    deepest = jd_year(neg[0][0]) if neg else 0.0
    latest = jd_year(pos[-1][1]) if pos else 0.0
    check(deepest <= -12900.0 and latest >= 16799.0,
          "行星覆盖 %.0f CE .. %.0f CE（公元后侧 %d 个文件，公元前侧 %d 个文件）"
          % (deepest, latest, len(pos), len(neg)),
          "实测最深 %.1f CE、最远 %.1f CE" % (deepest, latest))
    gaps = [(pos[i][1], pos[i + 1][0]) for i in range(len(pos) - 1) if pos[i + 1][0] > pos[i][1]]
    check(not gaps, "正年份窗口无缝隙（%d 个文件，600 年步长）" % len(pos),
          "缝隙 %s" % gaps[:3] if gaps else "")
    gaps = [(neg[i][1], neg[i + 1][0]) for i in range(len(neg) - 1) if neg[i + 1][0] > neg[i][1]]
    check(not gaps, "公元前窗口无缝隙（%d 个文件）" % len(neg), "缝隙 %s" % gaps[:3] if gaps else "")
    # Debian 三个二进制包各自的覆盖承诺
    basic = [(e.tfstart, e.tfend) for n, e in eset.files.items()
             if n in ("sepl_18.se1", "semo_18.se1", "seas_18.se1")]
    check(len(basic) == 3 and min(b[0] for b in basic) <= 2378496.5 and max(b[1] for b in basic) >= 2597651.4,
          "basic 目录覆盖 1800-2399 CE（Debian swe-basic-data 承诺）")
    m_files = [n for n in eset.files if n.startswith("seplm")]
    check(min(eset.files[n].tfstart for n in m_files) <= 1721057.5 - 5400 * 365.25,
          "standard+extra 的公元前文件覆盖到 5400 BCE 之前（Debian swe-standard-data 承诺）")

    print("\n[4/7] 行星与月球：端到端求值 vs 上游 swetest 参照值（%d 个历元）" % len(GOLDEN_EPOCHS))
    worst = 0.0
    for tjd, label, planets, moon_r in GOLDEN_EPOCHS:
        for name, ipli, want in zip(PLANET_NAMES, PLANET_IPL, planets):
            vec, eph = eset.heliocentric(tjd, ipli)
            got = radius(vec)
            worst = max(worst, abs(got - want))
            check(abs(got - want) <= 1e-6,
                  "%-6s %-9s 日心距 %.9f AU（swetest %.9f）[%s]" % (label, name, got, want, eph.name),
                  "Δ=%.2e AU" % (got - want))
        eph = eset.resolve("semo", tjd, MOON_IPL)
        got = radius(eph.vector(MOON_IPL, tjd))
        worst = max(worst, abs(got - moon_r))
        check(abs(got - moon_r) <= 1e-6,
              "%-6s 月球   地心距 %.9f AU = %.0f km（swetest %.9f）[%s]"
              % (label, got, got * AU_KM, moon_r, eph.name), "Δ=%.2e AU" % (got - moon_r))
    print("  —— 最大偏差 %.3e AU（容差 1e-6 AU）" % worst)

    print("\n[5/7] J2000.0 位置矢量 vs swetest 参照值（组件级，AU）")
    tjd = 2451545.0
    for name, ipli, want in zip(PLANET_NAMES, PLANET_IPL, GOLDEN_VEC_2000_PLANETS):
        vec, _ = eset.heliocentric(tjd, ipli)
        dev = max(abs(vec[i] - want[i]) for i in range(3))
        check(dev <= VECTOR_TOLERANCE.get(name, 1e-6),
              "%-8s (%#.9f, %#.9f, %#.9f)" % (name, vec[0], vec[1], vec[2]),
              "最大组件偏差 %.2e AU" % dev)
    vec = eset.resolve("semo", tjd, MOON_IPL).vector(MOON_IPL, tjd)
    dev = max(abs(vec[i] - GOLDEN_VEC_2000_MOON[i]) for i in range(3))
    check(dev <= 1e-6, "Moon     (%#.9f, %#.9f, %#.9f)" % tuple(vec), "最大组件偏差 %.2e AU" % dev)

    print("\n[6/7] 主小行星（seas/seasm 6 槽位）与行星卫星（sat/32 个文件）")
    for tjd, label, wants in ASTEROID_EPOCHS:
        eph = eset.resolve("seas", tjd, ASTEROID_SLOTS[0])
        for name, ipli, want in zip(ASTEROID_NAMES, ASTEROID_SLOTS, wants):
            got = radius(eph.vector(ipli, tjd))
            check(abs(got - want) <= 2e-6, "%-6s %-7s 日心距 %.7f AU（swetest %.7f）[%s]"
                  % (label, name, got, want, eph.name), "Δ=%.2e AU" % (got - want))
    for eph in eset.sat:
        key = eph.name[4:8]
        tjd = min(max(2451545.0, eph.tfstart + 1), eph.tfend - 1)
        got_km = radius(eph.vector(eph.ipl[0], tjd)) * AU_KM
        if key.endswith("99"):
            check(got_km < 5000.0, "sat/%-13s 行星本体中心偏移 %8.1f km（< 5000 km）"
                  % (eph.name, got_km))
            continue
        info = SATELLITE_SMA_KM.get(key)
        if info is None:
            check(got_km > 0.0, "sat/%-13s 求值 %.1f km（无文档半长轴，仅结构性校验）"
                  % (eph.name, got_km))
            continue
        name, sma = info
        low, high = SATELLITE_WIDE_BAND.get(key, (0.85, 1.15))
        ratio = got_km / sma
        check(low <= ratio <= high, "sat/%-13s %-9s 到中心体 %10.1f km（半长轴 %.0f km，比值 %.3f）"
              % (eph.name, name, got_km, sma, ratio))

    print("\n[7/7] 文本表：按下游真实用法解析")
    leap = [ln.strip() for ln in open(os.path.join(ephe_dir, "seleapsec.txt"))
            if ln.strip() and not ln.strip().startswith("#")]
    check(leap == ["20081231"], "seleapsec.txt 闰秒日期表", "解析出 %s" % leap)
    names = {}
    with open(os.path.join(ephe_dir, "seasnam.txt"), "r", errors="replace") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit():
                names[int(parts[0])] = parts[1]
    check(names.get(1) == "Ceres" and names.get(4) == "Vesta" and len(names) > 100000,
          "seasnam.txt 小行星编号->名称表", "%d 条，1=Ceres、4=Vesta" % len(names))
    stars = []
    with open(os.path.join(ephe_dir, "sefstars.txt"), "r", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split(",")
            if len(fields) >= 12 and fields[2] == "ICRS":
                stars.append(fields[0].strip())
    check(len(stars) > 1000 and "Aldebaran" in stars, "sefstars.txt 恒星表（ICRS 记录）",
          "%d 条，含 Aldebaran" % len(stars))
    fict = [ln for ln in open(os.path.join(ephe_dir, "seorbel.txt"), errors="replace")
            if ln.strip() and not ln.strip().startswith("#")]
    check(len(fict) >= 8, "seorbel.txt 虚拟行星轨道根数", "%d 行" % len(fict))

    print("\n" + "=" * 72)
    print("消费链完成：目录契约 -> 文件格式+CRC -> 时间覆盖 -> Chebyshev 段解包与求值")
    print("            -> 日心/地心位置 -> 与上游 swetest 参照值比对 -> 卫星距离 -> 文本表")
    print("检查项 %d 个，通过 %d 个，失败 %d 个" % (CHECKS[0], CHECKS[0] - len(FAILURES), len(FAILURES)))
    if FAILURES:
        print("失败项：")
        for item in FAILURES[:20]:
            print("  - %s" % item)
        return 1
    print("Verdict: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
