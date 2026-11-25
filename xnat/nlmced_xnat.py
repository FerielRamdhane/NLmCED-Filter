#!/usr/bin/env python3
"""
NLmCED filter - XNAT wrapper.

Uses the core NLmCED (nlmced.py from the nlmced image) for all processing, then:
  1. uploads the denoised DICOM series to the XNAT session as a new scan
  2. writes the dashboard files (raw true-intensity arrays, meta.txt, JPGs)
     to /output/<scan>_NLmCED_iter<..>_rho<..>_alpha<..>/  (-> resource NLmCED_images)

Called by the XNAT Container Service (see command.json):
  python /app/nlmced_xnat.py <iter> <rho> <alpha> <scan> <subject> <session> <project>

XNAT_HOST / XNAT_USER / XNAT_PASS are read from the environment variables that
the Container Service sets for every container (never passed on the command line).

Local test without XNAT (no upload; outputs in the mounted /output and /mount):
  docker run --rm -e NLMCED_SKIP_UPLOAD=1 -v <dicoms>:/input -v <out>:/output -v <dcm_out>:/mount \
      nlmced-xnat:1.1.0 python3.10 /app/nlmced_xnat.py 1 0.01 0.01 SCAN1 SUBJ SESS PROJ
"""
import os
import shutil
import sys
import tempfile

import numpy as np
import matplotlib.pyplot as plt  # backend already set to Agg by nlmced
import xnat

sys.path.insert(0, "/app")
import nlmced  # core module, same code as the EUCAIM image

INPUT_DIR = "/input"     # mount dicom-in
OUTPUT_DIR = "/output"   # mount filter-out  -> uploaded by XNAT as resource NLmCED_images
DICOM_DIR = "/mount"     # mount mount       -> denoised DICOMs, uploaded here as a new scan


def parse_xnat_args(argv):
    if len(argv) < 7:
        raise nlmced.NLmCEDError(
            "Usage: nlmced_xnat.py <iter> <rho> <alpha> <scan> <subject> <session> <project>")
    n_iter, rho, alpha = nlmced.parse_params(argv[:3])
    scan_id, subject_label, session_id, project = argv[3:7]
    return n_iter, rho, alpha, scan_id, subject_label, session_id, project


def xnat_credentials():
    host, user, pwd = (os.environ.get(k) for k in ("XNAT_HOST", "XNAT_USER", "XNAT_PASS"))
    if not (host and user and pwd):
        raise nlmced.NLmCEDError("XNAT_HOST / XNAT_USER / XNAT_PASS environment variables not set")
    return host, user, pwd


def write_dashboard_files(res, run_path):
    """
    Raw true-intensity float32 arrays (row-major) + meta.txt + plain JPGs, so the
    dashboard can do live window/level and show the exact pixel value on hover.

    3D: Slice_<z>_{original,filtered,residual}.{raw,jpg}           (unchanged from v1.0)
    4D: Vol_<v>_Slice_<z>_{original,filtered,residual}.{raw,jpg}  + numVolumes in meta.txt
    """
    norm, den, max_vals = res["original"], res["denoised"], res["max_vals"]
    n_z, n_vol = res["n_slices"], res["n_volumes"]
    rows, cols = norm.shape[:2]

    orig_true = norm * max_vals         # true intensity, same scale as source DICOM
    filt_true = den * max_vals
    resid_true = np.abs(orig_true - filt_true)

    # Same keys and order as v1.0 (the dashboard relies on them); new keys only at the end
    with open(os.path.join(run_path, "meta.txt"), "w") as f:
        f.write(f"rows={rows}\n")
        f.write(f"cols={cols}\n")
        f.write(f"numSlices={n_z}\n")
        f.write(f"originalMin={float(orig_true.min())}\n")
        f.write(f"originalMax={float(orig_true.max())}\n")
        f.write(f"filteredMin={float(filt_true.min())}\n")
        f.write(f"filteredMax={float(filt_true.max())}\n")
        f.write(f"residualMin={float(resid_true.min())}\n")
        f.write(f"residualMax={float(resid_true.max())}\n")
        f.write(f"numVolumes={n_vol}\n")
        f.write(f"toolVersion={nlmced.TOOL_VERSION}\n")

    for v in range(n_vol):
        prefix = f"Vol_{v + 1}_" if n_vol > 1 else ""
        for z in range(n_z):
            base = os.path.join(run_path, f"{prefix}Slice_{z + 1}_")
            orig_true[:, :, z, v].astype(np.float32).tofile(base + "original.raw")
            filt_true[:, :, z, v].astype(np.float32).tofile(base + "filtered.raw")
            resid_true[:, :, z, v].astype(np.float32).tofile(base + "residual.raw")

            plt.imsave(base + "original.jpg", norm[:, :, z, v], cmap="gray", vmin=0, vmax=1)
            plt.imsave(base + "filtered.jpg", den[:, :, z, v], cmap="gray", vmin=0, vmax=1)
            plt.imsave(base + "residual.jpg", np.abs(norm[:, :, z, v] - den[:, :, z, v]),
                       cmap="gray", vmin=0, vmax=0.05)


def upload_dicoms(dicom_dir, project, subject_label, session_id):
    host, user, pwd = xnat_credentials()
    with tempfile.TemporaryDirectory() as tmp:
        archive = shutil.make_archive(os.path.join(tmp, "Denoised"), "zip", dicom_dir)
        with xnat.connect(host, user=user, password=pwd) as session:
            experiment = session.projects[project].experiments[session_id]
            session.services.import_(archive,
                                     overwrite="none",
                                     project=project,
                                     subject=subject_label,
                                     experiment=experiment.label,
                                     content_type="application/zip")
    print("✓ Denoised DICOM series uploaded to XNAT")


def main():
    try:
        n_iter, rho, alpha, scan_id, subject_label, session_id, project = \
            parse_xnat_args(sys.argv[1:])

        # Parameter-encoded folder: different runs on the same scan don't overwrite each other
        run_path = os.path.join(OUTPUT_DIR, f"{scan_id}_NLmCED_iter{n_iter}_rho{rho}_alpha{alpha}")
        os.makedirs(run_path, exist_ok=True)
        print(f"Saving this run's outputs to: {run_path}")

        res = nlmced.run(INPUT_DIR, DICOM_DIR, n_iter, rho, alpha,
                         previews=False, matlab_dir=run_path)

        # Dashboard files first: they are in /output even if the upload fails
        write_dashboard_files(res, run_path)
        print("✓ Dashboard files written")

        if os.environ.get("NLMCED_SKIP_UPLOAD") == "1":
            print("⚠ NLMCED_SKIP_UPLOAD=1: upload to XNAT skipped (local test)")
        else:
            upload_dicoms(DICOM_DIR, project, subject_label, session_id)
    except nlmced.NLmCEDError as e:
        sys.exit(f"✗ {e}")


if __name__ == "__main__":
    main()
