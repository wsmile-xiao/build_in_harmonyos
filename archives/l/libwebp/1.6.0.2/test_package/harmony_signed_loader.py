"""OHOS-specific signature/ELF namespace contract, separate from C API consumer."""
import ctypes,hashlib,json,os,platform,re,struct,subprocess,sys
from pathlib import Path

def run(package,readelf):
    package=Path(package).resolve();lib=(package/'lib/libwebp.so').resolve()
    assert platform.uname().system=='HarmonyOS','NOT_ACTUAL_HARMONYOS'
    assert lib.is_relative_to(package) and lib.is_file()
    data=lib.read_bytes();assert data[:4]==b'\x7fELF' and data[4:6]==b'\x02\x01'
    assert struct.unpack_from('<H',data,18)[0]==183,'NOT_AARCH64'
    sections=subprocess.run([readelf,'-S',str(lib)],capture_output=True,text=True,check=True)
    assert '.codesign' in sections.stdout,'NO_OHOS_CODE_SIGNATURE'
    dynamic=subprocess.run([readelf,'-d',str(lib)],capture_output=True,text=True,check=True)
    needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',dynamic.stdout)
    assert needed and all('/' not in x for x in needed),'PATH_BEARING_DT_NEEDED'
    soname=re.findall(r'\(SONAME\).*?\[(.*?)\]',dynamic.stdout)
    assert len(soname)==1 and '/' not in soname[0]
    assert (package/'lib'/soname[0]).is_file() and (package/'lib'/soname[0]).resolve()==lib,'SONAME_NOT_REAL_INSTALLED_PROVIDER'
    codec=ctypes.CDLL(str(lib),mode=os.RTLD_LOCAL|os.RTLD_NOW)
    codec.WebPEncodeLosslessRGBA.argtypes=[ctypes.POINTER(ctypes.c_uint8),ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8))]
    codec.WebPEncodeLosslessRGBA.restype=ctypes.c_size_t
    codec.WebPDecodeRGBA.argtypes=[ctypes.POINTER(ctypes.c_uint8),ctypes.c_size_t,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]
    codec.WebPDecodeRGBA.restype=ctypes.POINTER(ctypes.c_uint8)
    codec.WebPFree.argtypes=[ctypes.c_void_p]
    rgba=(ctypes.c_uint8*4)(31,63,127,255);encoded=ctypes.POINTER(ctypes.c_uint8)()
    size=codec.WebPEncodeLosslessRGBA(rgba,1,1,4,ctypes.byref(encoded));assert size and encoded
    w=ctypes.c_int();h=ctypes.c_int();decoded=codec.WebPDecodeRGBA(encoded,size,ctypes.byref(w),ctypes.byref(h))
    assert decoded and w.value==h.value==1 and ctypes.string_at(decoded,4)==bytes(rgba)
    codec.WebPFree(decoded);codec.WebPFree(encoded)
    maps=Path('/proc/self/maps').read_text();mapped=set()
    for line in maps.splitlines():
        fields=line.split(None,5)
        if len(fields)==6 and '/libwebp.so' in fields[-1]:mapped.add(str(Path(fields[-1]).resolve()))
    assert mapped=={str(lib)},'FOREIGN_OR_AMBIGUOUS_WEBP_NAMESPACE'
    sharpyuv=set()
    for line in maps.splitlines():
        fields=line.split(None,5)
        if len(fields)==6 and '/libsharpyuv.so' in fields[-1]:sharpyuv.add(str(Path(fields[-1]).resolve()))
    assert sharpyuv and all(Path(p).is_relative_to(package) for p in sharpyuv),'FOREIGN_SHARPYUV_PROVIDER'
    result={'name':'harmony_signed_aarch64_codec_namespace','os':platform.uname().system,'library':str(lib),'sha256':hashlib.sha256(data).hexdigest(),'needed':needed,'soname':soname,'codesign_present':True,'actual_loader_and_codec_rc':0,'webp_mapping':sorted(mapped),'sharpyuv_mapping':sorted(sharpyuv)}
    print(json.dumps(result,sort_keys=True));print('HARMONY_TEST_COUNT=1\nHARMONY 1/1 PASS')

if __name__=='__main__':run(sys.argv[1],sys.argv[2])
