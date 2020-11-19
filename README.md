# The Fil memory profiler for Python

Your code reads some data, processes it, and uses too much memory.
In order to reduce memory usage, you need to figure out:

1. Where peak memory usage is, also known as the high-water mark.
2. What code was responsible for allocating the memory that was present at that peak moment.

That's exactly what Fil will help you find.
Fil an open source memory profiler designed for data processing applications written in Python, and includes native support for Jupyter.

At the moment it only runs on Linux and macOS.

> "Within minutes of using your tool, I was able to identify a major memory bottleneck that I never would have thought existed.  The ability to track memory allocated via the Python interface and also C allocation is awesome, especially for my NumPy / Pandas programs."
> 
> —Derrick Kondo

For more information, including an example of the output, see https://pythonspeed.com/products/filmemoryprofiler/

* [Fil vs. other Python memory tools](#other-tools)
* [Installation](#installation)
* [Using Fil](#using-fil)
    * [Measuring peak (high-water mark) memory usage in Jupyter](#peak-jupyter)
    * [Measuring peak memory usage for Python scripts](#peak-python)
    * [Debugging out-of-memory crashes in your code](#oom)
* [Reducing memory usage in your code](#reducing-memory-usage)
* [How Fil works](#how-fil-works)
    * [Fil and threading, with notes on NumPy and Zarr](#threading)
    * [What Fil tracks](#what-fil-tracks)

## <a name="other-tools">Fil vs. other Python memory tools</a>

There are two distinct patterns of Python usage, each with its own source of memory problems.

In a long-running server, memory usage can grow indefinitely due to memory leaks.
That is, some memory is not being freed.

* If the issue is in Python code, tools like [`tracemalloc`](https://docs.python.org/3/library/tracemalloc.html) and [Pympler](https://pypi.org/project/Pympler/) can tell you which objects are leaking and what is preventing them from being leaked.
* If you're leaking memory in C code, you can use tools like [Valgrind](https://valgrind.org).

Fil, however, is not aimed at memory leaks, but at the other use case: data processing applications.
These applications load in data, process it somehow, and then finish running.

The problem with these applications is that they can, on purpose or by mistake, allocate huge amounts of memory.
It might get freed soon after, but if you allocate 16GB RAM and only have 8GB in your computer, the lack of leaks doesn't help you.

Fil will therefore tell you, in an easy to understand way:

1. Where peak memory usage is, also known as the high-water mark.
2. What code was responsible for allocating the memory that was present at that peak moment.
3. This includes C/Fortran/C++/whatever extensions that don't use Python's memory allocation API (`tracemalloc` only does Python memory APIs).

This allows you to [optimize that code in a variety of ways](https://pythonspeed.com/datascience/).

## Installation

Assuming you're on macOS or Linux, and are using Python 3.6 or later, you can use either Conda or pip (or any tool that is pip-compatible and can install `manylinux2010` wheels).

### Conda

To install on Conda:

```console
$ conda install -c conda-forge filprofiler
```

### Pip

To install the latest version of Fil you'll need Pip 19 or newer.
You can check like this:

```console
$ pip --version
pip 19.3.0
```

If you're using something older than v19, you can upgrade by doing:

```
$ pip install --upgrade pip
```

If _that_ doesn't work, try running that in a virtualenv.

Assuming you have a new enough version of pip:

```console
$ pip install filprofiler
```

## Using Fil

### <a name="peak-jupyter">Measuring peak (high-water mark) memory usage in Jupyter</a>

To measure memory usage of some code in Jupyter you need to do three things:

1. Use an alternative kernel, "Python 3 with Fil".
   You can choose this kernel when you create a new notebook, or you can switch an existing notebook in the Kernel menu; there should be a "Change Kernel" option in there in both Jupyter Notebook and JupyterLab.
2. Load the extension by doing `%load_ext filprofiler`.
3. Add the `%%filprofile` magic to the top of the cell with the code you wish to profile.


![Screenshot of JupyterLab](https://raw.githubusercontent.com/pythonspeed/filprofiler/master/images/jupyter.png)

### <a name="peak-python">Measuring peak (high-water mark) memory usage for Python scripts</a>

Instead of doing:

```console
$ python yourscript.py --input-file=yourfile
```

Just do:

```
$ fil-profile run yourscript.py --input-file=yourfile
```

And it will generate a report.

As of version 0.11, you can also run it like this:

```
$ python -m filprofiler run yourscript.py --input-file=yourfile
```

### <a name="oom">Debugging out-of-memory crashes</a>

First, run `free` to figure out how much memory is available—in this case about 6.3GB—and then set a corresponding limit on virtual memory with `ulimit`:

```console
$ free -h
       total   used   free  shared  buff/cache  available
Mem:   7.7Gi  1.1Gi  6.3Gi    50Mi       334Mi      6.3Gi
Swap:  3.9Gi  3.0Gi  871Mi
$ ulimit -Sv 6300000
```

Then, run your program under Fil, and it will generate a SVG at the point in time when memory runs out:

```console
$ fil-profile run oom.py 
...
=fil-profile= Wrote memory usage flamegraph to fil-result/2020-06-15T12:37:13.033/out-of-memory.svg
```

## <a name="reducing-memory-usage">Reducing memory usage in your code</a>

You've found where memory usage is coming from—now what?

If you're using data processing or scientific computing libraries, I have written a relevant [guide to reducing memory usage](https://pythonspeed.com/datascience/).

## How Fil works

Fil uses the `LD_PRELOAD`/`DYLD_INSERT_LIBRARIES` mechanism to preload a shared library at process startup.
This shared library captures all memory allocations and deallocations and keeps track of them.

At the same time, the Python tracing infrastructure (used e.g. by `cProfile` and `coverage.py`) to figure out which Python callstack/backtrace is responsible for each allocation.

### Fil and threading, with notes on NumPy and Zarr {#threading}

In general, Fil will track allocations in threads correctly.

First, if you start a thread via Python, running Python code, that thread will get its own callstack for tracking who is responsible for a memory allocation.

Second, if you start a C thread, the calling Python code is considered responsible for any memory allocations in that thread.
This works fine... except for thread pools.
If you start a pool of threads that are not Python threads, the Python code that created those threads will be responsible for all allocations created during the thread pool's lifetime.

Therefore, in order to ensure correct memory tracking, Fil disables thread pools in  BLAS (used by NumPy), BLOSC (used e.g. by Zarr), OpenMP, and `numexpr`.
They are all set to use 1 thread, so calls should run in the calling Python thread and everything should be tracked correctly.

This has some costs:

1. This can reduce performance in some cases, since you're doing computation with one CPU instead of many.
2. Insofar as these libraries allocate memory proportional to number of threads, the measured memory usage might be wrong.

Fil does this for the whole program when using `fil-profile run`.
When using the Jupyter kernel, anything run with the `%%filprofile` magic will have thread pools disabled, but other code should run normally.

### What Fil tracks

Fil will track memory allocated by:

* Normal Python code.
* C code using `malloc()`/`calloc()`/`realloc()`/`posix_memalign()`.
* C++ code using `new` (including via `aligned_alloc()`).
* Anonymous `mmap()`s.
* Fortran 90 explicitly allocated memory (tested with gcc's `gfortran`).

Still not supported, but planned:

* `mremap()` (resizing of `mmap()`).
* File-backed `mmap()`.
  The semantics are somewhat different than normal allocations or anonymous `mmap()`, since the OS can swap it in or out from disk transparently, so supporting this will involve a different kind of resource usage and reporting.
* Other forms of shared memory, need to investigate if any of them allow sufficient allocation.
* Anonymous `mmap()`s created via `/dev/zero` (not common, since it's not cross-platform, e.g. macOS doesn't support this).
* `memfd_create()`, a Linux-only mechanism for creating in-memory files.
* Possibly `memalign`, `valloc()`, `pvalloc()`, `reallocarray()`. These are all rarely used, as far as I can tell.

## License

Copyright 2020 Hyphenated Enterprises LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
