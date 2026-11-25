#!/usr/bin/env python3
"""
NLmCED filter - core (general / EUCAIM) version.

Reads a DICOM series, denoises it with NLmCED and writes the denoised series
(as a new DICOM series) plus per-slice preview JPGs. No XNAT dependency.

Supports:
  * 3D series (one file per slice)                      -> filtered as one volume
  * 4D series (one file per slice per dynamic/offset,
    e.g. CEST Z-spectrum, DCE, multi-echo)              -> each 3D volume is
                                                           filtered separately
Usage:
  EUCAIM:  jobman submit -i nlmced -- <input_dir> <output_dir> [iter] [rho] [alpha]
  Docker:  docker run --rm -v <in>:/input -v <out>:/output nlmced:1.1.0 [iter] [rho] [alpha]
           docker run --rm -v <in>:/data/in -v <out>:/data/out nlmced:1.1.0 /data/in /data/out [iter] [rho] [alpha]

Other tools (e.g. the XNAT wrapper) can import this module and call run().
"""
import os
import sys
import time
import traceback

import numpy as np
import pydicom
from pydicom.uid import generate_uid, ExplicitVRLittleEndian

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

TOOL_VERSION = "1.1.0"

DEFAULT_ITER = 1
DEFAULT_RHO = 0.01
DEFAULT_ALPHA = 0.01


class NLmCEDError(Exception):
    """Error with a message meant for the user."""


# ----------------------------------------------------------------------------
# Arguments
# ----------------------------------------------------------------------------
def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def split_dirs(argv):
    """
    Accepts both call styles:
      <input_dir> <output_dir> [iter] [rho] [alpha]   (EUCAIM jobman)
      [iter] [rho] [alpha]                            (dirs from INPUT_DIR/OUTPUT_DIR, default /input /output)
    """
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    if argv and not _is_number(argv[0]):
        if len(argv) < 2 or _is_number(argv[1]):
            raise NLmCEDError("Usage: <input_dir> <output_dir> [iter] [rho] [alpha]")
        input_dir, output_dir, argv = argv[0], argv[1], argv[2:]
    return input_dir, output_dir, argv


def parse_params(argv):
    """Positional [iter] [rho] [alpha]; missing or invalid values -> defaults."""
    def get(i, default, cast):
        if len(argv) <= i:
            return default
        try:
            return cast(argv[i])
        except ValueError:
            print(f"Argument {i + 1} ('{argv[i]}') invalid. Using default: {default}")
            return default

    return (get(0, DEFAULT_ITER, int),
            get(1, DEFAULT_RHO, float),
            get(2, DEFAULT_ALPHA, float))


def check_params(n_iter, rho, alpha):
    if n_iter < 1:
        raise NLmCEDError(f"iter must be >= 1 (got {n_iter})")
    for name, val in (("rho", rho), ("alpha", alpha)):
        if not (0 < val <= 0.1):
            raise NLmCEDError(f"{name} must be in (0, 0.1] (got {val})")


# ----------------------------------------------------------------------------
# DICOM reading and 3D / 4D organisation
# ----------------------------------------------------------------------------
def find_dicoms(input_dir):
    """Return [(path, filename, header)] for every readable image DICOM."""
    found = []
    for dir_name, _, files in os.walk(input_dir):
        for fn in sorted(files):
            if "_NLmCED" in fn:
                continue
            path = os.path.join(dir_name, fn)
            try:
                hdr = pydicom.dcmread(path, stop_before_pixels=True)
            except Exception:
                continue
            if "Rows" not in hdr or "Columns" not in hdr:
                continue  # not an image (e.g. DICOMDIR, SR, ...)
            found.append((path, fn, hdr))
    return found


def slice_position(hdr):
    """Position of the slice along the slice normal (fallbacks if missing)."""
    ipp = hdr.get("ImagePositionPatient")
    iop = hdr.get("ImageOrientationPatient")
    if ipp is not None and iop is not None:
        row, col = np.array(iop[:3], float), np.array(iop[3:], float)
        return float(np.dot(np.cross(row, col), np.array(ipp, float)))
    if hdr.get("SliceLocation") is not None:
        return float(hdr.SliceLocation)
    return None


def volume_key(hdr):
    """Ordering of the 4th dimension (dynamic / offset / echo) within a slice."""
    tpi = hdr.get("TemporalPositionIdentifier")
    return (int(tpi) if tpi is not None else 0, int(hdr.get("InstanceNumber", 0)))


def organise(entries):
    """
    Group files into volumes.
    Returns grid[v][z] = (path, filename) with v = volume index, z = slice index.
    """
    if any(int(h.get("NumberOfFrames", 1)) > 1 for _, _, h in entries):
        raise NLmCEDError("Enhanced multi-frame DICOM (NumberOfFrames > 1) is not supported "
                          "in this version. Please export the series as one file per slice.")

    positions = [slice_position(h) for _, _, h in entries]

    if any(p is None for p in positions):
        print("⚠ No slice geometry in headers: treating series as 3D ordered by InstanceNumber")
        ordered = sorted(entries, key=lambda e: int(e[2].get("InstanceNumber", 0)))
        return [[(p, f) for p, f, _ in ordered]]

    by_pos = {}
    for (path, fn, hdr), pos in zip(entries, positions):
        by_pos.setdefault(round(pos, 3), []).append((path, fn, hdr))

    sorted_pos = sorted(by_pos)
    counts = {len(by_pos[p]) for p in sorted_pos}
    if len(counts) != 1:
        raise NLmCEDError(f"Inconsistent series: slices have different numbers of images "
                          f"({sorted(counts)}). Cannot build a regular 3D/4D volume.")
    n_vol = counts.pop()

    for p in sorted_pos:
        by_pos[p].sort(key=lambda e: volume_key(e[2]))

    return [[(by_pos[p][v][0], by_pos[p][v][1]) for p in sorted_pos]
            for v in range(n_vol)]


# ----------------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------------
def to_original_dtype(data, dtype):
    """Clip to the range of the original pixel type, then cast."""
    if np.issubdtype(dtype, np.integer):
        info = np.iinfo(dtype)
        data = np.clip(data, info.min, info.max)
    return data.astype(dtype)


def save_preview(orig, filt, title, path):
    fig = plt.figure()
    plt.title(title, fontdict={"family": "serif", "size": 15, "fontweight": "bold"})
    plt.subplots_adjust(top=0.65, hspace=0.3)
    plt.axis("off")
    small = {"family": "serif", "size": 9, "fontweight": "bold"}
    for i, (img, name, vmax) in enumerate(
            [(orig, "Original", 1), (filt, "NLmCED Filter", 1),
             (np.abs(orig - filt), "Residual Image", 0.05)], start=1):
        ax = fig.add_subplot(1, 3, i)
        ax.imshow(img, cmap="gray", vmin=0, vmax=vmax)
        ax.set_title(name, fontdict=small)
        ax.axis("off")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def denoised_name(fn):
    base, ext = os.path.splitext(fn)
    return f"{base}_NLmCED{ext or '.dcm'}" if ext.lower() in ("", ".dcm", ".ima") \
        else f"{fn}_NLmCED.dcm"


def limit_cpus():
    """
    The compiled MATLAB code starts a parallel pool with one worker per visible CPU core,
    and each worker is a full MATLAB process: on machines with many cores this runs out of
    memory ("Killed"). Restricting the CPU affinity BEFORE the MATLAB Runtime starts limits
    the number of workers (same effect as `docker run --cpuset-cpus`).
    NLMCED_MAX_WORKERS (default 2) sets the limit; 0 = no limit.
    """
    try:
        n = int(os.environ.get("NLMCED_MAX_WORKERS", "2"))
    except ValueError:
        n = 2
    if n <= 0 or not hasattr(os, "sched_setaffinity"):
        return
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) > n:
        os.sched_setaffinity(0, set(cpus[:n]))
        print(f"Limiting to {n} CPU cores / parallel workers (of {len(cpus)} available)")


# ----------------------------------------------------------------------------
# Processing (importable)
# ----------------------------------------------------------------------------
def run(input_dir, output_dir, n_iter=DEFAULT_ITER, rho=DEFAULT_RHO, alpha=DEFAULT_ALPHA,
        previews=True, matlab_dir=None):
    """
    Denoise the DICOM series in input_dir.

    input_dir   folder with the original DICOM series
    output_dir  where the denoised DICOM files are written
    previews    write per-slice comparison JPGs to <output_dir>/NLmCED_images
    matlab_dir  working folder given to the MATLAB function (default: output_dir);
                for 4D data one sub-folder per volume is used

    Returns a dict with the arrays [x, y, z, v] needed by other tools:
      original, denoised  (each volume normalised 0..1 by its own maximum),
      max_vals (one maximum per volume), n_slices, n_volumes, n_files
    """
    check_params(n_iter, rho, alpha)
    print(f"NLmCED v{TOOL_VERSION}")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")

    entries = find_dicoms(input_dir)
    if not entries:
        listing = os.listdir(input_dir) if os.path.isdir(input_dir) else "folder not found"
        raise NLmCEDError(f"No DICOM images found in {input_dir} (contents: {listing})")

    grid = organise(entries)
    n_vol, n_z = len(grid), len(grid[0])
    is_4d = n_vol > 1
    print(f"Series layout: {n_z} slices x {n_vol} volume(s) -> "
          f"{'4D: each volume filtered separately' if is_4d else '3D'}")
    if n_z < 2:
        raise NLmCEDError("NLmCED is a 3D filter: at least 2 slices per volume are required.")

    # Load pixel data -> data[x, y, z, v]
    datasets = [[pydicom.dcmread(p) for p, _ in vol] for vol in grid]
    ref = datasets[0][0]
    rows, cols = int(ref.Rows), int(ref.Columns)
    src_dtype = ref.pixel_array.dtype
    data = np.zeros((rows, cols, n_z, n_vol), dtype=np.float64)
    for v in range(n_vol):
        for z in range(n_z):
            px = datasets[v][z].pixel_array
            if px.shape != (rows, cols):
                raise NLmCEDError(f"Image size mismatch ({px.shape} vs {(rows, cols)}).")
            data[:, :, z, v] = px

    # Each volume is normalised by ITS OWN maximum (exactly like a 3D scan) and scaled
    # back by the same value afterwards, so the intensity ratios between volumes
    # (e.g. CEST Z-spectrum / S0) are preserved. A single global maximum made
    # low-signal volumes look almost empty to the filter, which then hangs.
    max_vals = data.max(axis=(0, 1, 2))  # one maximum per volume
    if np.any(max_vals <= 0):
        empty = [v + 1 for v in range(n_vol) if max_vals[v] <= 0]
        raise NLmCEDError(f"Empty volume(s) (max intensity <= 0): {empty}")
    norm = data / max_vals  # broadcasts over the last axis (volumes)

    limit_cpus()  # must run before the MATLAB Runtime starts
    try:
        import NLmCEDPkg
        nlmced = NLmCEDPkg.initialize()
    except Exception as e:
        raise NLmCEDError(f"Error initializing NLmCEDPkg package: {e}")

    os.makedirs(output_dir, exist_ok=True)
    matlab_dir = matlab_dir or output_dir

    print(f"Starting NLmCED with iter={n_iter}, rho={rho}, alpha={alpha} ...")
    denoised = np.zeros_like(norm)
    t_start = time.time()
    for v in range(n_vol):
        t_vol = time.time()
        work_dir = os.path.join(matlab_dir, f"vol_{v + 1:03d}") if is_4d else matlab_dir
        os.makedirs(work_dir, exist_ok=True)
        if is_4d:
            print(f"  volume {v + 1}/{n_vol}")
        try:
            denoised[:, :, :, v] = np.array(
                nlmced.NLmCED(np.ascontiguousarray(norm[:, :, :, v]),
                              int(n_iter), float(rho), float(alpha), work_dir))
        except Exception as e:
            traceback.print_exc()
            raise NLmCEDError(f"Error during NLmCED processing (volume {v + 1}): {e}")
        if is_4d:
            done = time.time() - t_start
            print(f"    done in {time.time() - t_vol:.0f} s "
                  f"(estimated remaining: {done / (v + 1) * (n_vol - v - 1) / 60:.1f} min)")
    print(f"✓ NLmCED processing completed in {(time.time() - t_start) / 60:.1f} min")

    if previews:
        preview_root = os.path.join(output_dir, "NLmCED_images")
        for v in range(n_vol):
            vdir = os.path.join(preview_root, f"vol_{v + 1:03d}") if is_4d else preview_root
            os.makedirs(vdir, exist_ok=True)
            for z in range(n_z):
                title = f"NLmCED filter for Slice N° {z + 1}" + (f" - Vol {v + 1}" if is_4d else "")
                save_preview(norm[:, :, z, v], denoised[:, :, z, v], title,
                             os.path.join(vdir, f"Slice_{z + 1}_NLmCED.jpg"))

    # Denoised series: one new SeriesInstanceUID for the whole series.
    # FrameOfReferenceUID is kept: geometry is unchanged by denoising.
    new_series_uid = generate_uid()
    suffix = f"_NLmCED_iter_{n_iter}_rho_{rho}_alpha_{alpha}"
    out_px = denoised * max_vals
    for v in range(n_vol):
        for z in range(n_z):
            ds = datasets[v][z]
            _, fn = grid[v][z]

            ds.SeriesInstanceUID = new_series_uid
            desc = str(ds.get("SeriesDescription", "")).split("_NLmCED")[0]
            ds.SeriesDescription = (desc + suffix)[:64]  # LO max length
            new_uid = generate_uid()
            ds.SOPInstanceUID = new_uid
            ds.file_meta.MediaStorageSOPInstanceUID = new_uid

            ds.PixelData = to_original_dtype(out_px[:, :, z, v], src_dtype).tobytes()
            if ds.file_meta.TransferSyntaxUID.is_compressed:
                ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
                ds.is_little_endian, ds.is_implicit_VR = True, False

            ds.save_as(os.path.join(output_dir, denoised_name(fn)))

    n_files = n_vol * n_z
    print(f"✓ {n_files} denoised DICOM files written to {output_dir}")
    return {"original": norm, "denoised": denoised, "max_vals": max_vals,
            "n_slices": n_z, "n_volumes": n_vol, "n_files": n_files}


def main():
    try:
        input_dir, output_dir, rest = split_dirs(sys.argv[1:])
        n_iter, rho, alpha = parse_params(rest)
        run(input_dir, output_dir, n_iter, rho, alpha)
    except NLmCEDError as e:
        sys.exit(f"✗ {e}")


if __name__ == "__main__":
    main()
