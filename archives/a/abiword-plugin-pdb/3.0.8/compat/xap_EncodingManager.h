/* compat/xap_EncodingManager.h — OHOS minimal AbiWord encoding shim
 *
 * The pdb importer includes this header but uses no EncodingManager
 * symbols; provide the class name so the include resolves.
 */
#ifndef XAP_ENCODINGMANAGER_H
#define XAP_ENCODINGMANAGER_H

class XAP_EncodingManager
{
public:
	XAP_EncodingManager () {}
	virtual ~XAP_EncodingManager () {}
};

#endif /* XAP_ENCODINGMANAGER_H */
