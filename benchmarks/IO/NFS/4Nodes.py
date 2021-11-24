import cv2
import zipfile
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
import time
import logging
import json
warnings.filterwarnings("ignore")
import sys
HEIGHT = 137
WIDTH = 236
SIZE = 128
loadfileid=int(sys.argv[1])
TRAIN = ['/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_0.parquet',
         '/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_1.parquet',
         '/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_2.parquet',
         '/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_3.parquet']
def bbox(img):
    rows = np.any(img, axis=1)
    cols = np.any(img, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return rmin, rmax, cmin, cmax

def crop_resize(img0, size=SIZE, pad=16):
    #crop a box around pixels large than the threshold 
    #some images contain line at the sides
    ymin,ymax,xmin,xmax = bbox(img0[5:-5,5:-5] > 80)
    #cropping may cut too much, so we need to add it back
    xmin = xmin - 13 if (xmin > 13) else 0
    ymin = ymin - 10 if (ymin > 10) else 0
    xmax = xmax + 13 if (xmax < WIDTH - 13) else WIDTH
    ymax = ymax + 10 if (ymax < HEIGHT - 10) else HEIGHT
    img = img0[ymin:ymax,xmin:xmax]
    #remove lo intensity pixels as noise
    img[img < 28] = 0
    lx, ly = xmax-xmin,ymax-ymin
    l = max(lx,ly) + pad
    #make sure that the aspect ratio is kept in rescaling
    img = np.pad(img, [((l-ly)//2,), ((l-lx)//2,)], mode='constant')
    return cv2.resize(img,(size,size))
load_start=0.0
load_finish=0.0
process_start=0.0
process_total_time=0.0
save_total_time=0.0
#with zipfile.ZipFile("result-{}.zip".format(loadfileid), 'w') as img_out:
print(TRAIN[loadfileid],flush=True)
load_start=time.time()
df = pd.read_parquet(TRAIN[loadfileid])
load_finish=time.time()
#the input is inverted
process_start=time.time()
data = 255 - df.values[:, 1:].reshape(-1, HEIGHT, WIDTH).astype(np.uint8)
for idx in range(len(df)):
    name = df.iloc[idx,0]
    #normalize each image by its max val
    #process_before=time.time()
    img = (data[idx]*(255.0/data[idx].max())).astype(np.uint8)
    img = crop_resize(img)
    img = cv2.imencode('.png',img)[1]
process_total_time=time.time()-process_start
# save_before=time.time()
# img_out.writestr(name + '.png', img)
# save_total_time+=time.time()-save_before
json.dump({
    "load_start":load_start,
    "load_finish":load_finish,
    "process_time":process_total_time,
    "save_time":save_total_time
},open("./4Nodes-{}.json".format(loadfileid),"w"),indent=4)