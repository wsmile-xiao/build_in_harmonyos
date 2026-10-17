/*
 * test_consumer.c — 消费者用例 (独立于上游测试与鸿蒙专项测试计数)
 *
 * 模拟业务上层组件: 仅通过 rdma-core 已安装/导出的公开头文件、公开 API、
 * 正常链接目标和运行时产物使用该三方库, 验证第三方使用者能否编译、链接、
 * 调用并正常运行:
 *   - 公开头: <infiniband/verbs.h>, <rdma/rdma_cma.h>
 *   - 公开 API: ibv_get_device_list / ibv_get_device_count /
 *               ibv_get_device_guid / rdma_get_devices
 *   - 可观察结果: 枚举设备并打印 name/guid (OHOS 无硬件时返回 0 设备,
 *                 API 调用链与释放路径仍完整执行)
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <infiniband/verbs.h>
#include <rdma/rdma_cma.h>
#include <arpa/inet.h>

static void print_guid(uint64_t guid)
{
	unsigned char b[8];
	int i;
	for (i = 0; i < 8; i++)
		b[i] = (unsigned char)(guid >> (8 * (7 - i)));
	printf("%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x", b[0], b[1], b[2], b[3],
	       b[4], b[5], b[6], b[7]);
}

int main(void)
{
	struct ibv_device **devs;
	struct ibv_context **rdma_ctxs;
	int ndevs = 0, nrdma = 0;
	int i;
	int rc = 0;

	printf("== rdma-core consumer validation (libibverbs + librdmacm public API) ==\n");

	/* 公开 API 1: libibverbs 设备枚举 (无硬件时 NULL/0 属正常) */
	devs = ibv_get_device_list(&ndevs);
	if (!devs && ndevs != 0) {
		fprintf(stderr, "consumer: ibv_get_device_list failed (ndevs=%d)\n", ndevs);
		return 1;
	}
	printf("libibverbs devices: %d\n", ndevs);
	for (i = 0; i < ndevs; i++) {
		if (!devs[i] || !devs[i]->name) {
			fprintf(stderr, "consumer: invalid device entry %d\n", i);
			rc = 1;
			break;
		}
		printf("  device %d: name=%s guid=", i, devs[i]->name);
		print_guid(ibv_get_device_guid(devs[i]));
		printf("\n");
	}
	if (devs)
		ibv_free_device_list(devs);

	/* 公开 API 2: librdmacm 设备枚举 (返回 ibv_context ** 数组) */
	rdma_ctxs = rdma_get_devices(&nrdma);
	if (!rdma_ctxs && nrdma != 0) {
		fprintf(stderr, "consumer: rdma_get_devices failed (nrdma=%d)\n", nrdma);
		return 2;
	}
	printf("librdmacm devices: %d\n", nrdma);
	for (i = 0; i < nrdma; i++) {
		if (!rdma_ctxs[i] || !rdma_ctxs[i]->device ||
		    !rdma_ctxs[i]->device->name) {
			fprintf(stderr, "consumer: invalid rdma context entry %d\n", i);
			rc = 2;
			break;
		}
		printf("  rdma device %d: %s\n",
		       i, rdma_ctxs[i]->device->name);
	}
	if (rdma_ctxs)
		rdma_free_devices(rdma_ctxs);

	if (rc == 0)
		printf("== consumer validation: PASS ==\n");
	else
		printf("== consumer validation: FAIL (rc=%d) ==\n", rc);
	return rc;
}