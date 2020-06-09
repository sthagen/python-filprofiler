from libc.stdlib cimport malloc, free, realloc
from libc.stdint cimport uint64_t

def pymalloc(size):
    return <uint64_t>malloc(size)

def pyfree(address: uint64_t):
    free(<void*>address)

def pyrealloc(address: uint64_t, size: uint64_t):
    return <uint64_t>realloc(<void*>address, size)
