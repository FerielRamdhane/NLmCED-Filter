# Non Local mean Coherence Enhancing Diffusion filter (NLmCED)
## Tool Overview

Tool Overview

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

## Docker Image Usage
```bash
docker run --rm \
  -v path_of_input:/input \
  -v path_of_output:/output \
  nlmced:latest python nlmced.py [iter] [rho] [alpha]
```
Where:
* path_of_input: Directory containing the original DICOM images for each patient

* path_of_output: Directory where the NLmCED-denoised DICOM images will be saved
## Citation
[1] F. Romdhane, F. Benzarti, A. Hamid, A new method for three-dimensional magnetic resonance images denoising. International Journal of Computational Vision and Robotics 2018 8:1, 1-17. DOI:10.1504/IJCVR.2018.090012

## License
This repository is licensed under the [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)](LICENSE). You may use and share the content non-commercially, with proper attribution, but you may not modify or create derivative works.




