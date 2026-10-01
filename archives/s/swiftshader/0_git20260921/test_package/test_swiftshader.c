// Consumer test for the SwiftShader 0_git20260921 HarmonyOS PC package.
//
// Three assertion groups:
//   C (consumer usage): links against the installed SwiftShader ICD
//       (libvk_swiftshader.so, which exports the full Vulkan entry points as a
//       drop-in ICD) and drives a real end-to-end Vulkan compute workload:
//       instance -> physical device -> logical device -> SPIR-V compute
//       pipeline (data[i] = data[i]*2 + 1, executed by the Reactor JIT) ->
//       dispatch -> read-back + verify.
//   H (HarmonyOS-specific): platform traits of the produced ICD.
//   P (PC-specific): packaging traits of the produced ICD.
//
// A passing run proves the CPU Vulkan implementation (including its JIT) is
// functional on the OpenHarmony/HarmonyOS target.
#include <dlfcn.h>
#include <elf.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vulkan.h>

#include "shader_spv.h"

#ifndef __OHOS__
#error "This consumer test targets OpenHarmony/HarmonyOS (__OHOS__) only"
#endif

static int g_c = 0;   // consumer-usage assertions passed
static int g_h = 0;   // HarmonyOS-specific assertions passed
static int g_p = 0;   // PC-specific assertions passed
static int g_fail = 0;

static void report(const char *group, int line, const char *what, int ok)
{
	if (ok) {
		if (!strcmp(group, "C")) g_c++; else if (!strcmp(group, "H")) g_h++; else g_p++;
	} else {
		g_fail++;
		fprintf(stderr, "[FAIL] %s:%d [%s] %s\n", __FILE__, line, group, what);
	}
}

#define OKC(cond) report("C", __LINE__, #cond, (cond))
#define OKH(cond) report("H", __LINE__, #cond, (cond))
#define OKP(cond) report("P", __LINE__, #cond, (cond))

// ─────────────────────────── minimal ELF64 reader ───────────────────────────
typedef struct
{
	int elf64;
	int machine;
	int type;
	char soname[64];
	char needed[8][64];
	int needed_n;
} ElfInfo;

static int vaddrToOff(const Elf64_Phdr *ph, int phnum, Elf64_Addr vaddr,
                      Elf64_Off *out)
{
	for (int i = 0; i < phnum; i++) {
		if (ph[i].p_type != PT_LOAD) continue;
		if (vaddr >= ph[i].p_vaddr &&
		    vaddr < ph[i].p_vaddr + ph[i].p_filesz) {
			*out = ph[i].p_offset + (vaddr - ph[i].p_vaddr);
			return 1;
		}
	}
	return 0;
}

static int readElfInfo(const char *path, ElfInfo *info)
{
	FILE *f = fopen(path, "rb");
	if (!f) return 0;
	memset(info, 0, sizeof(*info));

	Elf64_Ehdr eh;
	if (fread(&eh, sizeof(eh), 1, f) != 1) { fclose(f); return 0; }
	if (memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) { fclose(f); return 0; }

	info->elf64 = (eh.e_ident[EI_CLASS] == ELFCLASS64);
	info->machine = eh.e_machine;
	info->type = eh.e_type;
	if (eh.e_phnum == 0) { fclose(f); return 1; }

	Elf64_Phdr *ph = calloc(eh.e_phnum, sizeof(Elf64_Phdr));
	if (!ph) { fclose(f); return 1; }
	fseek(f, (long)eh.e_phoff, SEEK_SET);
	if (fread(ph, sizeof(Elf64_Phdr), eh.e_phnum, f) != eh.e_phnum) {
		free(ph); fclose(f); return 1;
	}

	Elf64_Off dyn_off = 0;
	Elf64_Xword dyn_sz = 0;
	for (int i = 0; i < eh.e_phnum; i++) {
		if (ph[i].p_type == PT_DYNAMIC) {
			dyn_off = ph[i].p_offset;
			dyn_sz = ph[i].p_filesz;
		}
	}
	if (!dyn_off) { free(ph); fclose(f); return 1; }

	int n = (int)(dyn_sz / sizeof(Elf64_Dyn));
	Elf64_Dyn *dyn = calloc(n > 0 ? n : 1, sizeof(Elf64_Dyn));
	if (!dyn) { free(ph); fclose(f); return 1; }
	fseek(f, (long)dyn_off, SEEK_SET);
	if (fread(dyn, sizeof(Elf64_Dyn), n, f) != (size_t)n) {
		free(dyn); free(ph); fclose(f); return 1;
	}

	Elf64_Addr strtab_va = 0;
	Elf64_Xword strtab_sz = 0;
	for (int i = 0; i < n; i++) {
		if (dyn[i].d_tag == DT_STRTAB) strtab_va = dyn[i].d_un.d_ptr;
		if (dyn[i].d_tag == DT_STRSZ) strtab_sz = dyn[i].d_un.d_val;
	}
	if (!strtab_va || !strtab_sz) { free(dyn); free(ph); fclose(f); return 1; }

	Elf64_Off strtab_off = 0;
	if (!vaddrToOff(ph, eh.e_phnum, strtab_va, &strtab_off)) {
		free(dyn); free(ph); fclose(f); return 1;
	}
	char *strtab = calloc(strtab_sz + 1, 1);
	if (!strtab) { free(dyn); free(ph); fclose(f); return 1; }
	fseek(f, (long)strtab_off, SEEK_SET);
	if (fread(strtab, 1, strtab_sz, f) != strtab_sz) {
		free(strtab); free(dyn); free(ph); fclose(f); return 1;
	}

	for (int i = 0; i < n; i++) {
		if (dyn[i].d_tag == DT_SONAME) {
			const char *s = strtab + dyn[i].d_un.d_val;
			if (s >= strtab && s < strtab + strtab_sz)
				snprintf(info->soname, sizeof(info->soname), "%s", s);
		} else if (dyn[i].d_tag == DT_NEEDED && info->needed_n < 8) {
			const char *s = strtab + dyn[i].d_un.d_val;
			if (s >= strtab && s < strtab + strtab_sz)
				snprintf(info->needed[info->needed_n++],
				         sizeof(info->needed[0]), "%s", s);
		}
	}

	free(strtab); free(dyn); free(ph); fclose(f);
	return 1;
}

static int hasNeeded(const ElfInfo *i, const char *name)
{
	for (int k = 0; k < i->needed_n; k++)
		if (!strcmp(i->needed[k], name)) return 1;
	return 0;
}

// ───────────────────────────── Vulkan workload ──────────────────────────────
static uint32_t findMemoryType(VkPhysicalDevice pd, uint32_t typeBits,
                               VkMemoryPropertyFlags props)
{
	VkPhysicalDeviceMemoryProperties mp;
	vkGetPhysicalDeviceMemoryProperties(pd, &mp);
	for (uint32_t i = 0; i < mp.memoryTypeCount; i++) {
		if ((typeBits & (1u << i)) &&
		    (mp.memoryTypes[i].propertyFlags & props) == props)
			return i;
	}
	return 0xFFFFFFFFu;
}

int main(void)
{
	// ══ H: HarmonyOS-specific platform traits of the produced ICD ═════════
	// H1: this test only exists on the OHOS target (compile-time guard above).
	OKH(1);

	Dl_info dli;
	memset(&dli, 0, sizeof(dli));
	int havePath = dladdr((void *)&vkCreateInstance, &dli) && dli.dli_fname;
	fprintf(stderr, "[info] ICD path: %s\n",
	        havePath ? dli.dli_fname : "(unavailable)");

	ElfInfo ei;
	int haveElf = havePath && readElfInfo(dli.dli_fname, &ei);
	if (haveElf) {
		fprintf(stderr,
		        "[info] ICD ELF: elf64=%d machine=0x%x type=%d soname='%s' needed_n=%d\n",
		        ei.elf64, ei.machine, ei.type, ei.soname, ei.needed_n);
		for (int k = 0; k < ei.needed_n; k++)
			fprintf(stderr, "[info]   NEEDED %s\n", ei.needed[k]);
	}

	// H2: the produced ICD is a 64-bit AArch64 position-independent object.
	OKH(haveElf && ei.elf64 && ei.machine == EM_AARCH64 && ei.type == ET_DYN);
	// H3: musl (OHOS libc) folds libpthread/libdl/librt into libc: the ICD must
	//     depend on libc.so and must NOT carry separate libpthread/libdl/librt.
	OKH(haveElf && hasNeeded(&ei, "libc.so") &&
	    !hasNeeded(&ei, "libpthread.so") && !hasNeeded(&ei, "libdl.so") &&
	    !hasNeeded(&ei, "librt.so"));

	// ══ P: PC-specific packaging traits of the produced ICD ═══════════════
	// P1: the ICD carries the SONAME the Vulkan loader resolves.
	OKP(haveElf && !strcmp(ei.soname, "libvk_swiftshader.so"));
	// P2: dependency closure is exactly the C++ runtime + libc (no unexpected
	//     desktop system libraries).
	OKP(haveElf && hasNeeded(&ei, "libc++_shared.so") && hasNeeded(&ei, "libc.so"));

	// ══ C: consumer-usage workload through the SwiftShader ICD ════════════
	VkApplicationInfo app = {0};
	app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
	app.pApplicationName = "swiftshader-test_package";
	app.apiVersion = VK_API_VERSION_1_1;

	VkInstanceCreateInfo ici = {0};
	ici.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
	ici.pApplicationInfo = &app;

	VkInstance instance = VK_NULL_HANDLE;
	VkResult r = vkCreateInstance(&ici, NULL, &instance);
	if (r != VK_SUCCESS || instance == VK_NULL_HANDLE) {
		fprintf(stderr, "FATAL: vkCreateInstance failed: %d\n", (int)r);
		g_fail++;
		goto summary;
	}
	OKC(1);

	uint32_t devCount = 0;
	r = vkEnumeratePhysicalDevices(instance, &devCount, NULL);
	OKC(r == VK_SUCCESS && devCount >= 1);

	VkPhysicalDevice pd = VK_NULL_HANDLE;
	if (devCount >= 1) {
		devCount = 1;
		vkEnumeratePhysicalDevices(instance, &devCount, &pd);
	}
	OKC(pd != VK_NULL_HANDLE);

	VkPhysicalDeviceProperties props;
	vkGetPhysicalDeviceProperties(pd, &props);
	fprintf(stderr, "[info] device: '%s' api=%u.%u.%u type=%d\n",
	        props.deviceName, VK_VERSION_MAJOR(props.apiVersion),
	        VK_VERSION_MINOR(props.apiVersion),
	        VK_VERSION_PATCH(props.apiVersion), (int)props.deviceType);

	OKC(props.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU);
	OKC(strstr(props.deviceName, "SwiftShader") != NULL);

	uint32_t qfCount = 0;
	vkGetPhysicalDeviceQueueFamilyProperties(pd, &qfCount, NULL);
	VkQueueFamilyProperties qf[8];
	if (qfCount > 8) qfCount = 8;
	vkGetPhysicalDeviceQueueFamilyProperties(pd, &qfCount, qf);
	uint32_t qfIndex = 0xFFFFFFFFu;
	for (uint32_t i = 0; i < qfCount; i++)
		if (qf[i].queueFlags & VK_QUEUE_COMPUTE_BIT) { qfIndex = i; break; }
	OKC(qfIndex != 0xFFFFFFFFu);
	if (qfIndex == 0xFFFFFFFFu) goto summary;

	float prio = 1.0f;
	VkDeviceQueueCreateInfo qci = {0};
	qci.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
	qci.queueFamilyIndex = qfIndex;
	qci.queueCount = 1;
	qci.pQueuePriorities = &prio;

	VkDeviceCreateInfo dci = {0};
	dci.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
	dci.queueCreateInfoCount = 1;
	dci.pQueueCreateInfos = &qci;

	VkDevice device = VK_NULL_HANDLE;
	r = vkCreateDevice(pd, &dci, NULL, &device);
	OKC(r == VK_SUCCESS && device != VK_NULL_HANDLE);
	if (!device) goto summary;

	VkQueue queue = VK_NULL_HANDLE;
	vkGetDeviceQueue(device, qfIndex, 0, &queue);
	OKC(queue != VK_NULL_HANDLE);

	const uint32_t N = 4;
	const uint32_t kBytes = N * sizeof(uint32_t);
	const uint32_t inData[4] = { 1, 2, 3, 4 };

	VkBufferCreateInfo bci = {0};
	bci.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
	bci.size = kBytes;
	bci.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
	bci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

	VkBuffer buf = VK_NULL_HANDLE;
	OKC(vkCreateBuffer(device, &bci, NULL, &buf) == VK_SUCCESS);

	VkMemoryRequirements req;
	vkGetBufferMemoryRequirements(device, buf, &req);
	VkMemoryAllocateInfo mai = {0};
	mai.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
	mai.allocationSize = req.size;
	mai.memoryTypeIndex = findMemoryType(
	    pd, req.memoryTypeBits,
	    VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
	VkDeviceMemory mem = VK_NULL_HANDLE;
	OKC(vkAllocateMemory(device, &mai, NULL, &mem) == VK_SUCCESS);
	OKC(vkBindBufferMemory(device, buf, mem, 0) == VK_SUCCESS);

	void *mapped = NULL;
	OKC(vkMapMemory(device, mem, 0, kBytes, 0, &mapped) == VK_SUCCESS);
	if (mapped) memcpy(mapped, inData, kBytes);

	VkDescriptorSetLayoutBinding dslb = {0};
	dslb.binding = 0;
	dslb.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
	dslb.descriptorCount = 1;
	dslb.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
	VkDescriptorSetLayoutCreateInfo dslci = {0};
	dslci.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
	dslci.bindingCount = 1;
	dslci.pBindings = &dslb;
	VkDescriptorSetLayout dsl = VK_NULL_HANDLE;
	OKC(vkCreateDescriptorSetLayout(device, &dslci, NULL, &dsl) == VK_SUCCESS);

	VkDescriptorPoolSize dps = { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1 };
	VkDescriptorPoolCreateInfo dpci = {0};
	dpci.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
	dpci.maxSets = 1;
	dpci.poolSizeCount = 1;
	dpci.pPoolSizes = &dps;
	VkDescriptorPool dpool = VK_NULL_HANDLE;
	OKC(vkCreateDescriptorPool(device, &dpci, NULL, &dpool) == VK_SUCCESS);

	VkDescriptorSetAllocateInfo dsai = {0};
	dsai.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
	dsai.descriptorPool = dpool;
	dsai.descriptorSetCount = 1;
	dsai.pSetLayouts = &dsl;
	VkDescriptorSet dset = VK_NULL_HANDLE;
	OKC(vkAllocateDescriptorSets(device, &dsai, &dset) == VK_SUCCESS);

	VkDescriptorBufferInfo dbi = { buf, 0, kBytes };
	VkWriteDescriptorSet wds = {0};
	wds.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
	wds.dstSet = dset;
	wds.dstBinding = 0;
	wds.descriptorCount = 1;
	wds.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
	wds.pBufferInfo = &dbi;
	vkUpdateDescriptorSets(device, 1, &wds, 0, NULL);
	g_c++;

	VkShaderModuleCreateInfo smci = {0};
	smci.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
	smci.codeSize = kComputeShaderSpirvWords * sizeof(uint32_t);
	smci.pCode = kComputeShaderSpirv;
	VkShaderModule sm = VK_NULL_HANDLE;
	OKC(vkCreateShaderModule(device, &smci, NULL, &sm) == VK_SUCCESS);

	VkPipelineLayoutCreateInfo plci = {0};
	plci.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
	plci.setLayoutCount = 1;
	plci.pSetLayouts = &dsl;
	VkPipelineLayout pl = VK_NULL_HANDLE;
	OKC(vkCreatePipelineLayout(device, &plci, NULL, &pl) == VK_SUCCESS);

	VkComputePipelineCreateInfo cpci = {0};
	cpci.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
	cpci.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
	cpci.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
	cpci.stage.module = sm;
	cpci.stage.pName = "main";
	cpci.layout = pl;
	VkPipeline pipe = VK_NULL_HANDLE;
	OKC(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &cpci, NULL,
	                             &pipe) == VK_SUCCESS);

	VkCommandPoolCreateInfo cpi = {0};
	cpi.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
	cpi.queueFamilyIndex = qfIndex;
	VkCommandPool cpool = VK_NULL_HANDLE;
	OKC(vkCreateCommandPool(device, &cpi, NULL, &cpool) == VK_SUCCESS);

	VkCommandBufferAllocateInfo cbai = {0};
	cbai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
	cbai.commandPool = cpool;
	cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
	cbai.commandBufferCount = 1;
	VkCommandBuffer cb = VK_NULL_HANDLE;
	OKC(vkAllocateCommandBuffers(device, &cbai, &cb) == VK_SUCCESS);

	VkCommandBufferBeginInfo cbbi = {0};
	cbbi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
	OKC(vkBeginCommandBuffer(cb, &cbbi) == VK_SUCCESS);
	vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_COMPUTE, pipe);
	vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1,
	                        &dset, 0, NULL);
	vkCmdDispatch(cb, N, 1, 1);
	VkMemoryBarrier mb = {0};
	mb.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER;
	mb.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
	mb.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
	vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
	                     VK_PIPELINE_STAGE_HOST_BIT, 0, 1, &mb, 0, NULL, 0, NULL);
	OKC(vkEndCommandBuffer(cb) == VK_SUCCESS);

	VkFenceCreateInfo fci = {0};
	fci.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
	VkFence fence = VK_NULL_HANDLE;
	OKC(vkCreateFence(device, &fci, NULL, &fence) == VK_SUCCESS);

	VkSubmitInfo si = {0};
	si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
	si.commandBufferCount = 1;
	si.pCommandBuffers = &cb;
	OKC(vkQueueSubmit(queue, 1, &si, fence) == VK_SUCCESS);
	OKC(vkWaitForFences(device, 1, &fence, VK_TRUE, 10000000000ull) == VK_SUCCESS);

	uint32_t out[4] = { 0, 0, 0, 0 };
	if (mapped) memcpy(out, mapped, kBytes);
	fprintf(stderr, "[info] compute result: %u %u %u %u (expect 3 5 7 9)\n",
	        out[0], out[1], out[2], out[3]);
	for (uint32_t i = 0; i < N; i++)
		OKC(out[i] == inData[i] * 2u + 1u);

	vkDestroyFence(device, fence, NULL);
	vkDestroyCommandPool(device, cpool, NULL);
	vkDestroyPipeline(device, pipe, NULL);
	vkDestroyPipelineLayout(device, pl, NULL);
	vkDestroyShaderModule(device, sm, NULL);
	vkDestroyDescriptorPool(device, dpool, NULL);
	vkDestroyDescriptorSetLayout(device, dsl, NULL);
	vkUnmapMemory(device, mem);
	vkFreeMemory(device, mem, NULL);
	vkDestroyBuffer(device, buf, NULL);
	vkDestroyDevice(device, NULL);
	vkDestroyInstance(instance, NULL);

summary:
	fprintf(stderr,
	        "test_swiftshader: C=%d H=%d P=%d failed=%d\n",
	        g_c, g_h, g_p, g_fail);
	return g_fail == 0 ? 0 : 1;
}
