#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
if [ "${#}" -ne 2 ]; then
  echo "Usage: build-kernel.sh SOURCE_BUNDLE_DIR FRESH_BUILD_DIR" >&2
  exit 2
fi
inputs="$(cd "${1}" && pwd)"
mkdir -p "${2}"
build="$(cd "${2}" && pwd)"
tools="$(cd "$(dirname "${0}")" && pwd)"
export KBUILD_BUILD_USER=community
export KBUILD_BUILD_HOST=cube-vadj1-build
export KBUILD_BUILD_VERSION=1
python3 "${tools}/prepare-source.py" --inputs "${inputs}" --build-root "${build}"
kernel="${build}/kernel"
make -C "${kernel}" ARCH=arm64 LLVM=1 LLVM_IAS=1 olddefconfig
cp "${kernel}/.config" "${build}/build.config"
make -C "${kernel}" -j"${JOBS:-2}" ARCH=arm64 LLVM=1 LLVM_IAS=1 Image.lzo modules > "${build}/baseline-build.log" 2>&1
cp "${kernel}/Module.symvers" "${build}/Module.symvers.baseline"
cp "${kernel}/vmlinux.symvers" "${build}/vmlinux.symvers.baseline"
cp "${kernel}/arch/arm64/boot/Image" "${build}/Image.baseline"
patch --batch --forward -d "${kernel}/common_drivers" -p1 -i "${inputs}/0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch"
test "$(sha256sum "${kernel}/common_drivers/drivers/media/enhancement/amvecm/amve.c" | cut -d ' ' -f 1)" = f896c6dbc29f53c1b58fd17a85bc48202e59b5fa61ec0136a89cbec547571db4
make -C "${kernel}" -j"${JOBS:-2}" ARCH=arm64 LLVM=1 LLVM_IAS=1 Image.lzo modules > "${build}/patched-build.log" 2>&1
cp "${kernel}/Module.symvers" "${build}/Module.symvers.corrected"
cp "${kernel}/vmlinux.symvers" "${build}/vmlinux.symvers.corrected"
cp "${kernel}/arch/arm64/boot/Image" "${build}/Image.corrected"
cp "${kernel}/arch/arm64/boot/Image.lzo" "${build}/Image.corrected.lzo"
echo "Built kernels in ${build}. Verify stock module compatibility before packaging."
