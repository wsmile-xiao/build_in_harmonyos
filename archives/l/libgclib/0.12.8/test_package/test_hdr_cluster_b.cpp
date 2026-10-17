/*
 * 消费者视角测试（续）—— 发运头文件集里的第二个「编译簇」
 *
 * test_libgclib.cpp 的 A 组断言「24 个发运头都能被消费者单独包含」，
 * 但这 24 个头在**一个 TU 里装不下**，必须拆成两个：
 *
 *   GHash.hh    : template <class OBJ> class GHash                 （char* 键）
 *   GHashMap.hh : template <class V, class Hash, class Eq,
 *                            typename khInt_t> class GHash         （4 参数）
 *
 * 两个 headerguard 不同、名字却相同，因此**任何** TU 同时包含二者都是
 * 硬错误：`too few template parameters in template redeclaration`。
 * 而 GFastaIndex.h → GHashMap.hh、GapAssem.h → GHash.hh，所以这两个
 * 传递闭包互斥：GHashMap 簇（GFastaIndex/GFaSeqGet/GHashMap/khashl/
 * wyhash/xxhash）留在 test_libgclib.cpp，本文件装 GHash 簇。
 *
 * 本 TU **不注册断言**：它存在的意义与 test_libgclib.cpp 里那 22 个
 * `#include` 完全一样 —— 能编译、能链接，就证明这一簇头自洽且其外部
 * 依赖（strhash / GMALLOC / GFREE / GError，均由 libgclib 导出）齐备。
 * 因此 test_libgclib.cpp 的 83 条断言数不受影响。
 */
#include "GBase.h"
#include "gdna.h"
#include "GFastaFile.h"
#include "GList.hh"
#include "GapAssem.h"   /* → GHash.hh（GHash 簇的入口之一） */
#include "GHash.hh"

/* 导出一个符号，使这个 TU 不能被编译器整体优化掉，
 * 也顺带验证「簇 B 的头被包含后」产出的目标文件仍能与 libgclib 链接。
 * 注意：**故意**不被 test_libgclib.cpp 调用 —— 本 TU 的契约是编译+链接，
 * 不是运行时行为（那些由 test_libgclib.cpp 的 83 条断言负责）。 */
extern "C" int gclib_hdr_cluster_b_anchor(void) {
    return 1;
}
