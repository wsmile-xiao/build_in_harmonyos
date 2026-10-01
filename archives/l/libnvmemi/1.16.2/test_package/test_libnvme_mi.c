// SPDX-License-Identifier: LGPL-2.1-or-later
/*
 * libnvmemi 1.16.2 —— 完整消费者用例（平台 rule12：真跑端到端业务流程）
 *
 * 本文件只使用交付物：共享库 libnvme-mi.so + 公共头 <libnvme-mi.h>。
 * 不写任何 assert()，结果全部用显式比对 + 计数器 + 退出码表达。
 *
 * 为什么要在进程内伪造 MCTP 设备
 *   NVMe-MI 的传输层是 AF_MCTP 原始套接字（内核 5.15+ 的 MCTP 子系统），
 *   CI 的鸿蒙 PC 上没有 MCTP 控制器，无法接真实设备。但 MI 协议层本身是
 *   完整可验证的业务逻辑，所以本用例用 ELF 符号介入（interposition）在
 *   同一进程里造一个"假 MCTP 设备"：
 *     · 介入 socket()：库发起的 socket(AF_MCTP, SOCK_DGRAM, 0) 换成一对
 *       AF_UNIX SOCK_DGRAM socketpair 的一端（另一端是本用例的设备侧）；
 *     · 介入 sendmsg()：截获库发出的 MI 请求报文，按 NVMe-MI 规范生成响应，
 *       从设备侧注入 socketpair —— 于是库自己的 poll()/recvmsg() 走的是
 *       真实内核收发路径，不需要再介入。
 *   库内部（nvme/mi-mctp.c 的 ops 表）调用的正是 libc 的 socket/sendmsg，
 *   而可执行文件的全局符号优先级最高（CMake 的 ENABLE_EXPORTS →
 *   -rdynamic/--export-dynamic），所以介入对共享库同样生效。
 *
 * 业务流程（4 段，逐段核对结果）
 *   ① nvme_mi_create_root + nvme_mi_open_mctp        —— 建立 MI 端点
 *   ② nvme_mi_scan_ep：MI Control Primitive
 *      "Read MI Data Structure / Controller List"     —— 枚举控制器
 *   ③ 逐个 nvme_mi_admin_identify_ctrl：MI Admin
 *      Identify Controller (CNS=1)                    —— 序列号/型号/VID/固件版本
 *                                                        与设备侧注入数据逐字段比对
 *   ④ 错误路径：不支持的 MI 数据结构、不支持的 Admin 命令 —— 库必须如实报错
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

#include <libnvme-mi.h>

#if defined(__BYTE_ORDER__) && (__BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__)
#error "本用例的设备侧数据按小端填写（OHOS PC / aarch64 均为小端）"
#endif

/* ------------------------------------------------------------------ *
 * 设备侧固定数据（消费者用例的黄金值）
 * ------------------------------------------------------------------ */
#define FAKE_NET        1
#define FAKE_EID        8
#define FAKE_VID        0x1000u
#define FAKE_SSVID      0x1d1du
#define FAKE_SN         "NVME-MI-FAKE00000001"
#define FAKE_MN         "HarmonyOS PC fake NVMe-MI device"
#define FAKE_FR         "1.16.2"
#define FAKE_CTRL_CNT   3

static const unsigned short g_ctrl_ids[FAKE_CTRL_CNT] = {1, 4, 5};

/* MCTP 消息类型字节：MCTP_TYPE_NVME(0x04) | MCTP_TYPE_MIC(0x80)
   —— 同时也是 MI 规范里的 NVME_MI_MSGTYPE_NVME。 */
#define FAKE_MCTP_TYPE  0x84u
/* 设备侧在 Admin 响应 cdw3 里回的错误状态（SF = cdw3 >> 17） */
#define FAKE_ADM_ERR_CDW3 0x800c0000u
/* OHOS 头里没有 AF_MCTP 时，上游 mi-mctp.c 自己 `#define AF_MCTP 45`。 */
#define FAKE_AF_MCTP    45

/* ------------------------------------------------------------------ *
 * 报文内固定偏移（相对"含 MCTP 类型字节的完整报文"）
 * nmp 字节（偏移 1）本用例只整体搬运，不解析，故不定义偏移宏。
 * ------------------------------------------------------------------ */
#define OFF_MI_OPCODE   4u                       /* struct nvme_mi_mi_req_hdr */
#define OFF_MI_CDW0     8u
#define OFF_ADM_OPCODE  4u                       /* struct nvme_mi_admin_req_hdr */
#define OFF_ADM_FLAGS   5u
#define OFF_ADM_DOFF    28u
#define OFF_ADM_DLEN    32u
#define OFF_ADM_CDW10   44u
#define OFF_RESP_STATUS 4u                       /* MI/Admin 响应头都是 status 在字节 4 */
#define MI_RESP_HDR     8u                       /* sizeof(struct nvme_mi_mi_resp_hdr) */
#define ADM_RESP_HDR    20u                      /* sizeof(struct nvme_mi_admin_resp_hdr) */
#define MIC_LEN         4u

#define BUFSZ           8192u

/* ------------------------------------------------------------------ *
 * 小端读写助手（不依赖库内部宏）
 * ------------------------------------------------------------------ */
static void put16(uint8_t *p, unsigned v)
{
	p[0] = (uint8_t)(v & 0xffu);
	p[1] = (uint8_t)((v >> 8) & 0xffu);
}

static void put32(uint8_t *p, uint32_t v)
{
	p[0] = (uint8_t)(v & 0xffu);
	p[1] = (uint8_t)((v >> 8) & 0xffu);
	p[2] = (uint8_t)((v >> 16) & 0xffu);
	p[3] = (uint8_t)((v >> 24) & 0xffu);
}

static uint32_t get32(const uint8_t *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	       ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* ------------------------------------------------------------------ *
 * MIC：CRC-32C（反射多项式 0x82F63B78），与库内 nvme_mi_crc32_update 同算法；
 * 覆盖 [MCTP 类型字节][响应头][数据]（不含 MIC 自身）。
 * ------------------------------------------------------------------ */
static uint32_t crc32c(uint32_t crc, const void *buf, size_t len)
{
	const uint8_t *p = (const uint8_t *)buf;

	while (len--) {
		int i;

		crc ^= *p++;
		for (i = 0; i < 8; i++)
			crc = (crc >> 1) ^ ((crc & 1u) ? 0x82F63B78u : 0u);
	}
	return crc;
}

static uint32_t fake_mic(const void *buf, size_t len)
{
	return ~crc32c(0xffffffffu, buf, len);
}

/* ------------------------------------------------------------------ *
 * 假 MCTP 设备
 * ------------------------------------------------------------------ */
static int g_cli_fd = -1;                /* 交给库的那一端 */
static int g_dev_fd = -1;                /* 设备侧这一端 */
static struct nvme_id_ctrl g_identify;   /* 设备侧 Identify Controller 数据 */

/* 设备侧收到的报文计数（用例末尾打印，作为"确实发生了真实收发"的证据） */
static unsigned g_req_mi, g_req_admin, g_req_identify, g_req_unsupported;

static int fake_device_init(void)
{
	int sv[2];

	if (syscall(SYS_socketpair, AF_UNIX, SOCK_DGRAM, 0, sv) != 0)
		return -1;
	g_cli_fd = sv[0];
	g_dev_fd = sv[1];

	memset(&g_identify, 0, sizeof(g_identify));
	g_identify.vid = FAKE_VID;
	g_identify.ssvid = FAKE_SSVID;
	memcpy(g_identify.sn, FAKE_SN, strlen(FAKE_SN));
	memcpy(g_identify.mn, FAKE_MN, strlen(FAKE_MN));
	memcpy(g_identify.fr, FAKE_FR, strlen(FAKE_FR));
	g_identify.rab = 6;
	g_identify.cntlid = 1;
	g_identify.ver = 0x00020000u;
	g_identify.mntmt = 0x0001u;
	g_identify.mxtmt = 0x0001u;
	return 0;
}

/* 按请求生成响应；out 为"含 MCTP 类型字节的完整响应"，*out_len 含 MIC */
static int fake_device_respond(const uint8_t *req, size_t req_len,
			       uint8_t *out, size_t *out_len)
{
	uint8_t nmp;
	unsigned mt;

	if (req_len < 8)
		return -1;
	nmp = req[0];                       /* 偏移 -1：类型字节被库切掉了 */
	mt = (nmp >> 3) & 0xfu;

	memset(out, 0, BUFSZ);
	out[0] = FAKE_MCTP_TYPE;
	out[1] = (uint8_t)(nmp | ((unsigned)NVME_MI_ROR_RSP << 7));

	if (mt == NVME_MI_MT_MI) {
		unsigned opcode = req[OFF_MI_OPCODE - 1];
		unsigned dtyp = req[OFF_MI_CDW0 - 1 + 3];

		g_req_mi++;
		if (opcode == (unsigned)nvme_mi_mi_opcode_mi_data_read &&
		    dtyp == (unsigned)nvme_mi_dtyp_ctrl_list) {
			uint8_t *data = out + MI_RESP_HDR;
			unsigned i;

			out[OFF_RESP_STATUS] = NVME_MI_RESP_SUCCESS;
			/* struct nvme_ctrl_list { __le16 num; __le16 identifier[2047]; } */
			put16(data, FAKE_CTRL_CNT);
			for (i = 0; i < FAKE_CTRL_CNT; i++)
				put16(data + 2 + 2 * i, g_ctrl_ids[i]);
			*out_len = MI_RESP_HDR + 2 + 2 * (size_t)2047 + MIC_LEN;
		} else {
			/* 不支持的数据结构类型 → MI 层错误状态 */
			g_req_unsupported++;
			out[OFF_RESP_STATUS] = NVME_MI_RESP_INVALID_CMD_SIZE;
			*out_len = MI_RESP_HDR + MIC_LEN;
		}
	} else if (mt == NVME_MI_MT_ADMIN) {
		unsigned opcode = req[OFF_ADM_OPCODE - 1];
		unsigned cns = get32(req + OFF_ADM_CDW10 - 1) & 0xffu;
		uint32_t doff = get32(req + OFF_ADM_DOFF - 1);
		uint32_t dlen = get32(req + OFF_ADM_DLEN - 1);

		g_req_admin++;
		out[OFF_RESP_STATUS] = NVME_MI_RESP_SUCCESS;
		if (opcode == 0x06u /* nvme_admin_identify */ && cns == 1u /* CNS=Controller */) {
			uint8_t *data = out + ADM_RESP_HDR;
			size_t avail = sizeof(g_identify);
			size_t take = dlen;

			g_req_identify++;
			if (take > sizeof(g_identify))
				take = sizeof(g_identify);
			if (doff < avail) {
				size_t have = avail - doff;

				if (take > have)
					take = have;
				memcpy(data, (const uint8_t *)&g_identify + doff, take);
			} else {
				take = 0;
			}
			*out_len = ADM_RESP_HDR + take + MIC_LEN;
		} else {
			/* 不支持的 Admin 命令 → 在 Admin 响应 cdw3(SF) 里回 NVMe 状态：
			   SF=0x4006（SC=内部错误 + M/DNR 位），库按 cdw3>>17 取状态，
			   消费者侧用公共头 nvme_status_get_value() 应读回同一个值。 */
			g_req_unsupported++;
			put32(out + 16, FAKE_ADM_ERR_CDW3);
			*out_len = ADM_RESP_HDR + MIC_LEN;
		}
	} else {
		g_req_unsupported++;
		out[OFF_RESP_STATUS] = NVME_MI_RESP_INVALID_CMD_SIZE;
		*out_len = MI_RESP_HDR + MIC_LEN;
	}

	put32(out + *out_len - MIC_LEN, fake_mic(out, *out_len - MIC_LEN));
	return 0;
}

/* ---------------- ELF 符号介入：socket / sendmsg ---------------- */
int socket(int domain, int type, int protocol)
{
	if (domain == FAKE_AF_MCTP) {
		if (g_cli_fd < 0) {
			errno = ENOENT;
			return -1;
		}
		return g_cli_fd;
	}
	return (int)syscall(SYS_socket, domain, type, protocol);
}

ssize_t sendmsg(int fd, const struct msghdr *msg, int flags)
{
	uint8_t req[BUFSZ];
	uint8_t resp[BUFSZ];
	size_t n = 0, rlen = 0;
	unsigned long i;

	if (fd != g_cli_fd)
		return (ssize_t)syscall(SYS_sendmsg, fd, msg, flags);

	for (i = 0; i < msg->msg_iovlen; i++) {
		size_t l = msg->msg_iov[i].iov_len;

		if (n + l > sizeof(req)) {
			errno = EMSGSIZE;
			return -1;
		}
		memcpy(req + n, msg->msg_iov[i].iov_base, l);
		n += l;
	}
	if (fake_device_respond(req, n, resp, &rlen) != 0) {
		errno = EIO;
		return -1;
	}
	/* 把响应注入设备侧 → 库的 poll()/recvmsg() 从内核缓冲区取到它 */
	if (rlen > 1 && send(g_dev_fd, resp + 1, rlen - 1, 0) < 0)
		return -1;
	return (ssize_t)n;
}

/* ------------------------------------------------------------------ *
 * 结果记录（不用 assert：显式比对 + 计数）
 * ------------------------------------------------------------------ */
static unsigned g_checks, g_fails;

static void check(int ok, const char *fmt, ...)
{
	va_list ap;

	g_checks++;
	if (!ok)
		g_fails++;
	printf("[%s] ", ok ? "ok  " : "FAIL");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
	fflush(stdout);
}

int main(void)
{
	nvme_root_t root;
	nvme_mi_ep_t ep;
	nvme_mi_ctrl_t ctrl, first_ctrl = NULL;
	unsigned n_ctrl = 0;
	int rc;

	if (fake_device_init() != 0) {
		printf("FAIL 无法创建内部 socketpair 伪造 MCTP 设备: %s\n", strerror(errno));
		return 1;
	}

	/* ① 建立 MI 端点 */
	root = nvme_mi_create_root(stderr, LOG_ERR);
	check(root != NULL, "nvme_mi_create_root() 返回 MI 根对象");
	if (!root)
		return 1;
	nvme_mi_set_probe_enabled(root, false);   /* 无真实硬件，关掉 quirk 探测 */

	ep = nvme_mi_open_mctp(root, FAKE_NET, FAKE_EID);
	check(ep != NULL, "nvme_mi_open_mctp(net=%d, eid=%d) 建立 MCTP 端点",
	      FAKE_NET, FAKE_EID);
	if (!ep) {
		nvme_mi_free_root(root);
		return 1;
	}
	check(nvme_mi_ep_get_timeout(ep) > 0, "端点默认超时 = %u ms", nvme_mi_ep_get_timeout(ep));

	/* ② MI Control Primitive：读控制器列表 → 枚举控制器 */
	rc = nvme_mi_scan_ep(ep, false);
	check(rc == 0, "nvme_mi_scan_ep() 读取控制器列表 rc=%d", rc);
	check(g_req_mi >= 1, "设备侧收到 %u 条 MI 报文（Control Primitive）", g_req_mi);

	for (ctrl = nvme_mi_first_ctrl(ep); ctrl; ctrl = nvme_mi_next_ctrl(ep, ctrl)) {
		unsigned id = nvme_mi_ctrl_id(ctrl);
		struct nvme_id_ctrl idbuf;
		char sn[sizeof(idbuf.sn) + 1], mn[sizeof(idbuf.mn) + 1], fr[sizeof(idbuf.fr) + 1];

		if (!first_ctrl)
			first_ctrl = ctrl;
		check(n_ctrl < FAKE_CTRL_CNT && id == g_ctrl_ids[n_ctrl],
		      "枚举到第 %u 个控制器 id=%u（设备侧宣布 %u）",
		      n_ctrl + 1, id, n_ctrl < FAKE_CTRL_CNT ? g_ctrl_ids[n_ctrl] : 0);

		/* ③ MI Admin Identify Controller */
		memset(&idbuf, 0, sizeof(idbuf));
		rc = nvme_mi_admin_identify_ctrl(ctrl, &idbuf);
		check(rc == 0, "nvme_mi_admin_identify_ctrl(ctrl=%u) rc=%d", id, rc);
		if (rc == 0) {
			memcpy(sn, idbuf.sn, sizeof(idbuf.sn));
			sn[sizeof(idbuf.sn)] = '\0';
			memcpy(mn, idbuf.mn, sizeof(idbuf.mn));
			mn[sizeof(idbuf.mn)] = '\0';
			memcpy(fr, idbuf.fr, sizeof(idbuf.fr));
			fr[sizeof(idbuf.fr)] = '\0';
			check(strncmp(sn, FAKE_SN, strlen(FAKE_SN)) == 0,
			      "SN 与设备侧一致：'%s'", sn);
			check(strncmp(mn, FAKE_MN, strlen(FAKE_MN)) == 0,
			      "MN 与设备侧一致：'%s'", mn);
			check(strncmp(fr, FAKE_FR, strlen(FAKE_FR)) == 0,
			      "FR 与设备侧一致：'%s'", fr);
			check(idbuf.vid == FAKE_VID && idbuf.ssvid == FAKE_SSVID,
			      "VID/SSVID 与设备侧一致：0x%04x/0x%04x",
			      idbuf.vid, idbuf.ssvid);
			check(idbuf.rab == g_identify.rab && idbuf.cntlid == g_identify.cntlid,
			      "RAB=%u CNTLID=%u 与设备侧一致", idbuf.rab, idbuf.cntlid);
		}
		n_ctrl++;
	}
	check(n_ctrl == FAKE_CTRL_CNT, "共枚举到 %u 个控制器（设备侧宣布 %u 个）",
	      n_ctrl, FAKE_CTRL_CNT);
	check(g_req_identify >= FAKE_CTRL_CNT,
	      "设备侧收到 %u 条 MI Admin Identify（≥ 控制器数 %u）",
	      g_req_identify, FAKE_CTRL_CNT);

	/* ④ 错误路径：不支持的 MI 数据结构 + 不支持的 Admin 命令 */
	{
		struct nvme_mi_read_port_info pinfo;
		const char *msg;

		memset(&pinfo, 0, sizeof(pinfo));
		rc = nvme_mi_mi_read_mi_data_port(ep, 0, &pinfo);
		check(rc == NVME_MI_RESP_INVALID_CMD_SIZE,
		      "不支持的 MI 数据结构（port_info）返回设备侧状态 %d（期望 %d）",
		      rc, NVME_MI_RESP_INVALID_CMD_SIZE);
		msg = nvme_mi_status_to_string(NVME_MI_RESP_INVALID_CMD_SIZE);
		check(msg != NULL && strstr(msg, "size") != NULL,
		      "nvme_mi_status_to_string(INVALID_CMD_SIZE) = '%s'",
		      msg ? msg : "(null)");
	}
	if (first_ctrl) {
		/* 挑一个方向位不是 bidirectional 的命令（0x7f 会被库在本地拒绝），
		   设备侧对非 Identify 的 Admin 命令一律回 NVME_SC_INVALID_OPCODE */
		rc = nvme_mi_admin_admin_passthru(first_ctrl, nvme_admin_get_features,
						  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
						  0, NULL, 0, NULL, 0, NULL);
		check(rc != 0 && nvme_status_get_value(rc) == (int)(FAKE_ADM_ERR_CDW3 >> 17),
		      "不支持的 Admin 命令(Get Features) 返回设备侧状态值 0x%x（期望 0x%x，rc=0x%x）",
		      nvme_status_get_value(rc), (int)(FAKE_ADM_ERR_CDW3 >> 17), rc);
	}
	check(g_req_unsupported >= 2, "设备侧收到 %u 条不支持的请求（MI、Admin 各 1）",
	      g_req_unsupported);

	printf("\n设备侧计数：MI=%u Admin=%u Identify=%u 不支持=%u\n",
	       g_req_mi, g_req_admin, g_req_identify, g_req_unsupported);
	printf("消费者用例结果：%u 项检查，%u 项失败\n", g_checks, g_fails);

	nvme_mi_close(ep);
	nvme_mi_free_root(root);
	if (g_dev_fd >= 0)
		close(g_dev_fd);
	return g_fails ? 1 : 0;
}
