#!/usr/bin/env python3
import pydicom 
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import os
import numpy as np 
import xnat
import shutil
import matplotlib.pyplot as plt
import random
import sys
import traceback

# Default values
DEFAULT_ITER = 1
DEFAULT_RHO = 0.01
DEFAULT_ALPHA = 0.01


def get_arg(index, default, cast_type):
    try:
        return cast_type(sys.argv[index])
    except IndexError:
        print(f"Argument {index} missing. Using default: {default}")
        return default
    except ValueError:
        print(f"Argument {index} invalid. Using default: {default}")
        return default

# def in_xnat():
#     """Detect if running inside XNAT Container Service."""
#     return len(sys.argv) > 8

def main():
    # NOW import the MATLAB package inside main()

    # print(os.environ['LD_LIBRARY_PATH'].split(':'))
    try:
        import NLmCEDPkg
        my_NLmCEDPkg = NLmCEDPkg.initialize()
    except Exception as e:
        print('Error initializing NLmCEDPkg package: {}'.format(e))
        exit(1)

    PathDicom = os.environ.get("INPUT_DIR", "/input")
    outputpath = os.environ.get("OUTPUT_DIR", "/output")

    print(f"Processing DICOM files from: {PathDicom}")
    
    # # Parse arguments with defaults
    # iter = get_arg(1, DEFAULT_ITER, int)
    # rho = get_arg(2, DEFAULT_RHO, float)
    # alpha = get_arg(3, DEFAULT_ALPHA, float)



    args = sys.argv[1:]
    iter  = int(args[0]) if len(args) > 0 else DEFAULT_ITER
    rho   = float(args[1]) if len(args) > 1 else DEFAULT_RHO
    alpha = float(args[2]) if len(args) > 2 else DEFAULT_ALPHA
    

    lstFilesDCM = []
    names =[]
    for dirName, subdirList, fileList in os.walk(PathDicom):
        for filename in fileList:
            pathdicom = os.path.join(dirName, filename)
            try:
                pydicom.dcmread(pathdicom, stop_before_pixels=True)
                if "_NLmCED" not in filename:
                    lstFilesDCM.append(pathdicom)
                    names.append(filename)
            except:
                continue

    if not lstFilesDCM:
        print("❌ No DICOM files found in /input")
        print("Contents of /input:", os.listdir(PathDicom))
        sys.exit(1)
    RefDs = pydicom.filereader.dcmread(lstFilesDCM[0])

    # Load dimensions based on the number of rows, columns, and slices (along the Z axis)
    ConstPixelDims = (int(RefDs.Rows), int(RefDs.Columns), len(lstFilesDCM))

    # The array is sized based on 'ConstPixelDims'
    ArrayDicom = np.zeros(ConstPixelDims, dtype=RefDs.pixel_array.dtype)
    Oldorder = np.zeros(len(lstFilesDCM))
    DS = []

    # loop through all the DICOM files
    for filenameDCM in lstFilesDCM:
        # read the file
        ds = pydicom.filereader.dcmread(filenameDCM)
        Oldorder[lstFilesDCM.index(filenameDCM)] = ds.InstanceNumber
        nindex = ds.InstanceNumber
        print(f"Processing instance: {nindex-1}")
        ArrayDicom[:, :, nindex-1] = ds.pixel_array # well reordered
        DS.append(ds)

    maxvall = ArrayDicom.max()
    Oldorder = Oldorder.astype(int)
    newnames = list(range(len(names)))
    DS_newnames = list(range(len(names))) # None]*len(Oldorder)

    for i in np.arange(0,len(Oldorder)): 
        inx = Oldorder[i]
        newnames[inx-1] = names[i]
        DS_newnames[inx-1] = DS[i]

    normzimage = np.zeros([ConstPixelDims[0],ConstPixelDims[1],ConstPixelDims[2]])

    for xx in np.arange(0,ConstPixelDims[0]):
        for yy in np.arange(0,ConstPixelDims[1]):
            for zz in np.arange(0,ConstPixelDims[2]):
                 normzimage[xx,yy,zz]= ArrayDicom[xx,yy,zz] / maxvall

        
    print(f"Starting NLmCED processing with iter={iter}, rho={rho}, alpha={alpha} ...")

    dicometa = DS_newnames[0]
    foldername = os.path.join(outputpath, "NLmCED_images")
    os.makedirs(foldername, exist_ok=True)

    try:
        DenoisedData = np.array(
            my_NLmCEDPkg.NLmCED(np.array(normzimage), int(iter), float(rho), float(alpha), outputpath)
        )
        print("✓ NLmCED processing completed successfully")
    except Exception as e:
        print(f"✗ Error during NLmCED processing: {e}")
        traceback.print_exc()
        sys.exit(1)


    ## Calculate the residual and save the images 
    indfilt = 0
    font1 = {'family':'serif','color':'black','size':15, 'fontweight':'bold'} 
    font2 = {'family':'serif','color':'black','size':9, 'fontweight':'bold'}

    for indfilt in np.arange(0,ConstPixelDims[2]):
        difference = np.abs(normzimage[:,:,indfilt]-DenoisedData[:,:,indfilt])

        fig = plt.figure()
        plt.title('NLmCED filter for Slice N° ' + str(indfilt+1), fontdict = font1)
        plt.subplots_adjust(top=0.65, hspace=0.3) 
        plt.axis('off')

        ax = fig.add_subplot(1,3,1)
        ax.imshow(normzimage[:,:,indfilt], cmap='gray', vmin=0, vmax=1)
        ax.set_title('Original', fontdict = font2)
        plt.axis('off')

        ax = fig.add_subplot(1,3,2)
        ax.imshow(DenoisedData[:,:,indfilt], cmap='gray', vmin=0, vmax=1) 
        ax.set_title('NLmCED Filter', fontdict = font2)
        plt.axis('off')

        ax = fig.add_subplot(1,3,3)
        ax.imshow(difference, cmap='gray', vmin=0, vmax=0.05)
        ax.set_title('Residual Image', fontdict = font2)
        plt.axis('off')
        
        namejpeg = newnames[indfilt]
        namejpeg = namejpeg.replace('.dcm', '')
        fig.savefig(foldername + '/' +  'Slice_' + str(indfilt+1)+'_NLmCED.jpg',  dpi=150)
        plt.close(fig)
        indfilt =+1

    # new serieInstance to generate new scan 
    os.chdir('..')
    # regenerate new UID
  
    dicometa = DS_newnames[0]
    
    elem2 = dicometa.SeriesInstanceUID 
    idexlast2 = elem2.rfind(".")
    newSeriesInstanceUID = elem2[0:idexlast2+1] + str(int(elem2[idexlast2+1:len(elem2)]) + 100)

    for idicom in np.arange(0,ConstPixelDims[2]):
        dico = DS_newnames[idicom]
        dico.SeriesInstanceUID = newSeriesInstanceUID

        elem01 = dico[0x0008, 0x103e].value
        newelem01 = ''.join(elem01)
        if newelem01.rfind("_NLmCED") == -1: 
            dico.SeriesDescription = str(newelem01) + str('_NLmCED') + str('_iter_') + str(iter) + str('_rho_') + str(rho) + str('_alpha_') + str(alpha)
        else:  
            dico.SeriesDescription = str(newelem01) + str('_iter_') + str(iter) + str('_rho_') + str(rho) + str('_alpha_') + str(alpha) 
        new_uid = generate_uid()        
        dico.SOPInstanceUID = new_uid
        dico.file_meta.MediaStorageSOPInstanceUID = new_uid
        dico.FrameOfReferenceUID = new_uid
          
        
        # get the new denoised data 
        Denmax =  DenoisedData[:,:,idicom] 
        dataNLmCED = maxvall * Denmax # Now scale by maximum 
        newimg = dataNLmCED.astype(np.uint16) 
        dico.PixelData  = newimg.tobytes()

        namedenoised = str(newnames[idicom])
        namedenoised  = namedenoised.replace('.dcm', '_NLmCED.dcm')
        dico.save_as(outputpath +'/'+ namedenoised)
        

if __name__ == '__main__':
    main()



