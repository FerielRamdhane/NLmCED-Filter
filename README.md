# Non Local mean Coherence Enhancing Diffusion filter (NLmCED)
## Tool Overview
The NLmCED filter is a hybrid denoising method that combines Non-Local Means (NLM) filtering with Coherence-Enhancing Anisotropic Diffusion, incorporating a Rician noise estimator for MRI images.

The NLM filter exploits the similarity between image patches to reduce noise by replacing each pixel with a weighted average of similar patches across the image. This approach effectively suppresses noise while preserving edges and fine structural details.

Anisotropic diffusion, on the other hand, is a diffusion-based filtering technique that selectively smooths homogeneous regions while preserving strong edges. This is achieved by guiding the diffusion process using local gradient information and a diffusion tensor.

By combining these two techniques, NLmCED benefits from the strong noise-reduction capability of NLM while maintaining the edge-preserving properties of anisotropic diffusion. This hybrid strategy produces superior denoising performance, particularly for MRI data, by effectively reducing noise while preserving important anatomical structures.

## Usage
User need to set up the input parameters such as : 
- iter: number of iteration
- rho (ρ): A standard deviation of the Gaussian kernel for the creation of the structure tensor [0, 0.1]
- alpha(α): A single value to control the diffusion tensor matrix [0, 0.1]

## Default parameters

* iter = 1
* ρ = 0.01
* α = 0.01

## Usage on EUCAIM
```bash
jobman submit -i nlmced -- <input_dir> <output_dir> [iter] [rho] [alpha]
```

## Docker Image Usage
```bash
docker run --rm \
  -v path_of_input:/input \
  -v path_of_output:/output \
  nlmced:1.1.0 [iter] [rho] [alpha]
```
or with explicit folders:
```bash
docker run --rm -v path_of_input:/data/in -v path_of_output:/data/out \
  nlmced:1.1.0 /data/in /data/out [iter] [rho] [alpha]
```

## Input data
* **3D series**: the whole volume is filtered at once.
* **4D series** (e.g. CEST Z-spectrum, dynamic or multi-echo acquisitions, stored as one file per slice per volume): the images are grouped by slice position and each 3D volume is filtered separately with the same parameters. Each volume is normalised by its own maximum before filtering and scaled back by the same value afterwards, so the relative intensities between volumes are preserved.
* Enhanced multi-frame DICOM (all frames in one file) is not supported yet.

## Outputs
* `*_NLmCED.dcm`: the denoised images, saved as a new DICOM series (new SeriesInstanceUID, same geometry).
* `NLmCED_images/`: preview JPGs per slice (original, filtered, residual); one sub-folder per volume for 4D data.

## Memory and parallel workers
The filter uses a MATLAB parallel pool; each worker is a separate MATLAB process. To avoid running out of memory, the number of workers is limited to **2** by default. Set the environment variable `NLMCED_MAX_WORKERS` to change it (`0` = one worker per CPU core), e.g. `docker run -e NLMCED_MAX_WORKERS=4 ...`.

## Changelog
* **1.1.0**: support for 4D series (per-volume filtering); fixed slice ordering when InstanceNumber does not start at 1; one SeriesInstanceUID / FrameOfReferenceUID for the whole denoised series; output keeps the original pixel type; input/output folders can be passed as arguments (EUCAIM jobman); parallel workers limited (default 2) to avoid out-of-memory; image reduced from 11.1 GB (minimal MATLAB Runtime, multi-stage build); container runs as the `eucaim` user (UID/GID 2323).
* **1.0**: first release.

## Repository layout
```
src/       core code (nlmced.py), Python requirements, compiled MATLAB package - shared by both images
eucaim/    self-contained image (minimal MATLAB Runtime installed in the build, UID 2323) - published on EUCAIM Harbor
xnat/      XNAT Container Service image: built on the shared MATLAB Runtime base used by all XNAT tools,
           adds upload to XNAT and the dashboard outputs (nlmced_xnat.py, command.json)
```

## Building the images
Both images are built from the repository root and always get the version written in `src/nlmced.py`.

**EUCAIM (self-contained)**
`./build.sh eucaim`  → `nlmced:<version>`. The minimal MATLAB Runtime (R2024b Update 5, same products as the
shared XNAT runtime base) is installed during the build from MathWorks' runtime installer image;
no MATLAB installation is needed.

**XNAT**
`./build.sh xnat`  → `nlmced-xnat:<version>`, on top of the shared base `mcr-riciannoiselevel:r2024b`
(another base can be given with `MCR_BASE=<image> ./build.sh xnat`). Then register `xnat/command.json` in the Container Service.

## Citation
[1] F. Romdhane, F. Benzarti, A. Hamid, A new method for three-dimensional magnetic resonance images denoising. International Journal of Computational Vision and Robotics 2018 8:1, 1-17. DOI:10.1504/IJCVR.2018.090012

## License
This repository is licensed under the [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)](LICENSE). You may use and share the content non-commercially, with proper attribution, but you may not modify or create derivative works.

## Citation 
Cite the code [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20642369.svg)](https://doi.org/10.5281/zenodo.20642369)
## Organization
[Euro-BioImaging](https://www.eurobioimaging.eu) · [Institute of Biostructures and Bioimaging (IBB) of the National Research Council (CNR)](https://www.ibb.cnr.it) · [University of Tunis El Manar](https://utm.rnu.tn/utm/fr)

