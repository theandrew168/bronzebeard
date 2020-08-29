import ctypes
import mmap

libc = ctypes.cdll.LoadLibrary(None)

mmap_func = libc.mmap
mmap_func.restype = ctypes.c_void_p
mmap_func.argtypes = (
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_size_t)

addr = mmap_func(None, mmap.PAGESIZE,
    mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC,
    mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
    -1, 0)

if addr == -1:
    raise OSError('mmap failed to allocated memory')

code = b'\x48\xc7\xc0\x2a\x00\x00\x00\xc3'
print(code)

ctypes.memmove(addr, code, len(code))

meaning_of_life = ctypes.cast(addr, ctypes.CFUNCTYPE(ctypes.c_long))

print(meaning_of_life())
