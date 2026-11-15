# Building the October Cube test package

The test release includes `Cube-VADJ1-20261030-test1-source.tar.gz`, containing
the pinned Linux, common_drivers, BL30 and original CoreELEC recipe sources,
the official embedded configuration, GPIO generator, correction and these
build/verification scripts. Original licenses remain inside the source archives.
The original recipe archive has 18 driver patches; the VADJ1 correction is
supplied separately and applied after the baseline build.

The published kernel was built on ARM64 Ubuntu 24.04 with Ubuntu Clang/LLD
17.0.6. It was checked against every shipped module. Stock used Android Clang
17.0.2; this is a compatible rebuild, not a byte-identical reproduction of the
official kernel. Build timestamps also affect the resulting image bytes.

Use a native ARM64 Linux environment with LLVM 17 tools in `PATH`, GNU make,
a host C compiler, flex, bison, bc, OpenSSL/libelf development files, GNU awk,
lzop, Python 3, tar and patch. Verification/extraction also uses squashfs-tools,
zstd and cpio. Use a fresh build directory with sufficient space.

After extracting the source bundle, from its root:

```sh
export PATH=/usr/lib/llvm-17/bin:$PATH
bash tools/build-kernel.sh "$PWD" "$PWD/build"
```

This builds an uncorrected baseline, applies the correction and rebuilds the
kernel. The corrected `amve.c` must have SHA-256:

```
f896c6dbc29f53c1b58fd17a85bc48202e59b5fa61ec0136a89cbec547571db4
```

Download the [original October update](https://github.com/SamuriHL/CoreELEC/releases/download/v22.0-samurihl-20261030200017/CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl-EXPERIMENTAL_20261030200017.tar)
as `stock-update.tar` and verify SHA-256:

```
9949947f35fb64ca3ab0ef81a6d96a6fba069908765382fd971f88acccb25a4c
```

Extract the official system modules and compare their imports with the build:

```sh
mkdir stock-update
tar -xf stock-update.tar -C stock-update
unsquashfs -d stock-system stock-update/CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017/target/SYSTEM
python3 tools/verify-module-abi.py \
  --stock-root stock-system \
  --symvers build/Module.symvers.corrected \
  --baseline-symvers build/Module.symvers.baseline \
  --output corrected-module-abi.json
```

The pinned official initramfs contains no `.ko` files. If adapting this process
to another release, inspect its initramfs and add any extracted modules as
another `--stock-root`; do not assume the same layout or compatibility.

With a passing report, package the update:

```sh
python3 tools/package-update.py stock-update.tar build/Image.corrected.lzo \
  corrected-module-abi.json \
  CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017-cube-vadj1-test1.tar
```

The packager checks all 236 archive entries, preserves all member metadata,
and permits changes only to `target/KERNEL` and `target/KERNEL.md5`. The
Android header's kernel size and standard boot ID are updated; its initramfs
and all other header fields are preserved. A verification report and SHA-256
file are written alongside the archive.

Read the build logs. The corrected build should introduce no warning absent
from the baseline. Symbol CRC and packaging checks cannot establish boot or
playback correctness; test the resulting update on a Cube before wider use.
