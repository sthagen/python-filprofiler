#!/bin/bash
set -euo pipefail
mkdir /tmp/home
mkdir /tmp/wheel
export HOME=/tmp/home
cd /src
mkdir -p dist
make target/release/libpymemprofile_api.a


rm -f filprofiler/_filpreload.o
rm -f filprofiler/_filpreload*.so
rm -f filprofiler/_filpreload*.dylib
rm -rf build

/opt/python/cp36-cp36m/bin/python3 setup.py bdist_wheel -d /tmp/wheel

/opt/python/cp37-cp37m/bin/python3 setup.py bdist_wheel -d /tmp/wheel

/opt/python/cp38-cp38/bin/python3 setup.py bdist_wheel -d /tmp/wheel

auditwheel repair --plat manylinux1_x86_64 -w dist/ /tmp/wheel/filprofiler*cp36*whl
auditwheel repair --plat manylinux1_x86_64 -w dist/ /tmp/wheel/filprofiler*cp37*whl
auditwheel repair --plat manylinux1_x86_64 -w dist/ /tmp/wheel/filprofiler*cp38*whl

