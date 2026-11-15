# Fire TV Cube 3: VADJ1 correction test branch

This community branch adds the measured raised-black correction to SamuriHL's
**v22.0-samurihl-20261030200017** release, commit
`bd95c331afe287a23f1851aab685fb2c6aa4907b`.

The October release retains the same affected `amve.c` as the September build.
The correction detects T7 VPP0 hardware still enabling VADJ1 while STB Dolby
Vision bypass requests it off, and reuses the existing direct/RDMA disable path.
It preserves the other register bits, Dolby-generated settings, and the intended
DV-to-HDR10 processing path.

## Source change

The correction is carried by:

```
projects/Amlogic-ce/packages/linux-drivers/amlogic/common_drivers/patches/0023-amvecm-t7-reconcile-vadj1-dv-bypass.patch
```

Matching assertions check the helper and both write-path call sites. No other
picture-processing source change is introduced. The resulting `amve.c` is
byte-identical to the correction previously validated on two Cubes using the
September release. The October kernel still requires its own compatibility and
hardware validation; prior tests do not establish that this new build works.

[Detailed findings, original captures, raw readings and maintainer checklist](https://github.com/Radmeister/coreelec-cube-dv-fix/blob/main/TECHNICAL.md).

## Building

Use the usual CoreELEC build environment for this source branch:

```sh
PROJECT=Amlogic-ce DEVICE=Amlogic-no ARCH=aarch64 make image
```

The common_drivers recipe applies patch 0023 during the build. This modifies the
host media driver in the kernel; a replacement `dovi.ko` is unnecessary.

The community update package is assembled from the verified official October
update with a rebuilt matching kernel. Its official system image, initramfs,
device trees, bootloader files and licenses are preserved. The kernel checksum
is updated. The release's stock embedded kernel configuration is used for the
rebuild, and shipped-module ABI checks are required before publishing the test
archive. Build/packaging verification results accompany the release.

## Testing the update

Use the community `.tar` attached to this fork's test release only after its
build verification is complete. It is intended for **Fire TV Cube 3** testing;
do not apply the older September kernel installer after updating.

1. Keep a full backup and a known-working recovery/update archive.
2. Copy the verified community update `.tar` into `/storage/.update/`.
3. Reboot into CoreELEC using the Cube's configured boot method.
4. Check the running guard:

   ```sh
   cat /sys/module/aml_media/parameters/pq_vadj1_sync
   ```

   It should report `Y`.
5. Play the same affected DV file repeatedly through Plex, then another file,
   checking the same dark scene. Confirm the intended HDR10 output is retained.

### Copying the update from Windows

Download the community `.tar` and its matching `.tar.sha256` from the test
release. In PowerShell, check the download:

```powershell
Get-FileHash -Algorithm SHA256 .\CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017-cube-vadj1-test1.tar
Get-Content .\CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017-cube-vadj1-test1.tar.sha256
```

The hash must match. Enable SSH in CoreELEC if necessary, then replace
`CUBE_IP` below with the test Cube's IP address:

```powershell
scp .\CoreELEC-Amlogic-no.aarch64-22.0-Piers-samurihl_20261030200017-cube-vadj1-test1.tar root@CUBE_IP:/storage/.update/
```

Windows OpenSSH supplies `scp`; WinSCP can also copy the same archive to
`/storage/.update/`. Leave only the intended update archive in that directory.
Once the copy finishes, reboot from CoreELEC's power menu. Use the Cube's SSH
password when prompted; it is not supplied by this project.

### Copying the update from macOS or Linux

Check `shasum -a 256 <archive.tar>` against the supplied checksum file, then use
`scp <archive.tar> root@CUBE_IP:/storage/.update/` and reboot from CoreELEC.

The correction survives a reboot. Installing a later stock build can replace
the corrected kernel; use a package compiled for that release or a maintainer
build that includes the source correction.

## Package verification tools

`tools/cube-vadj1/verify-module-abi.py` reads the official modules' ARM64 ELF
version records. It compares every imported symbol CRC with the rebuilt
exports or a retained stock module provider, checks vermagic, and optionally
requires baseline and corrected export sets to match exactly. These are
compatibility checks; a passing report does not prove runtime correctness.

`tools/cube-vadj1/package-update.py` accepts only the pinned official October
archive. It preserves the Android boot header and exact initramfs, replacing
the compressed kernel and updating its boot ID. It then replaces only
`target/KERNEL` and `target/KERNEL.md5` in the update archive and verifies the
contents and metadata of every archive entry. The published verification
report and SHA-256 identify the resulting test download.

Keep Kodi add-on updates on notification-only mode if using the workaround for
the separately observed startup/update deadlock. That issue is independent of
this kernel correction.

This is an independent community test build, not a SamuriHL/CoreELEC release or
endorsement. Do not overwrite a working reference device before verifying a test
Cube. The VADJ1 change activates only on T7 VPP0 in the specified DV bypass state.
