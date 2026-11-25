#!/usr/bin/env python3
"""
Show how much signal each slice of each volume has, to find "empty" slices
(no anatomy) that make the NLmCED MATLAB code hang.

Run with the nlmced image:
  docker run --rm --entrypoint python3.10 -v "<dicom folder>:/data/in" -v "<this tools folder>:/tools" nlmced:1.1.0 /tools/check_slices.py /data/in
"""
import sys
import numpy as np
import pydicom

sys.path.insert(0, "/app")
import nlmced as n

folder = sys.argv[1] if len(sys.argv) > 1 else "/data/in"
grid = n.organise(n.find_dicoms(folder))
data = np.array([[pydicom.dcmread(p).pixel_array.astype(float) for p, _ in vol] for vol in grid])
# data[v, z, x, y]
gmax = data.max()
print(f"{len(grid)} volume(s) x {len(grid[0])} slices, global max = {gmax:.0f}\n")
print("Mean signal of each slice, in % of the global maximum (* = below 1%)")
print("vol  " + "".join(f"  z{z + 1:<4}" for z in range(data.shape[1])) + "   all-zero slices")
for v in range(data.shape[0]):
    means = data[v].mean(axis=(1, 2)) / gmax * 100
    zeros = [z + 1 for z in range(data.shape[1]) if data[v, z].max() == 0]
    row = "".join(f"{m:6.2f}{'*' if m < 1 else ' '}" for m in means)
    print(f"{v + 1:3d}  {row}   {zeros if zeros else ''}")
