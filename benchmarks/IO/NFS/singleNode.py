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
HEIGHT = 137
WIDTH = 236
SIZE = 128

TRAIN = ['/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_0.parquet',
         '/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_1.parquet',
         '/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_2.parquet',
         '/nfs-storage/default-nfstest-pvc-a83881ec-36dd-4888-ad19-7dcebda55145/train_image_data_3.parquet']

OUT_TRAIN = 'train.zip'


def bbox(img):
    rows = np.any(img, axis=1)
    cols = np.any(img, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return rmin, rmax, cmin, cmax


def crop_resize(img0, size=SIZE, pad=16):
    # crop a box around pixels large than the threshold
    # some images contain line at the sides
    ymin, ymax, xmin, xmax = bbox(img0[5:-5, 5:-5] > 80)
    # cropping may cut too much, so we need to add it back
    xmin = xmin - 13 if (xmin > 13) else 0
    ymin = ymin - 10 if (ymin > 10) else 0
    xmax = xmax + 13 if (xmax < WIDTH - 13) else WIDTH
    ymax = ymax + 10 if (ymax < HEIGHT - 10) else HEIGHT
    img = img0[ymin:ymax, xmin:xmax]
    # remove lo intensity pixels as noise
    img[img < 28] = 0
    lx, ly = xmax-xmin, ymax-ymin
    l = max(lx, ly) + pad
    # make sure that the aspect ratio is kept in rescaling
    img = np.pad(img, [((l-ly)//2,), ((l-lx)//2,)], mode='constant')
    return cv2.resize(img, (size, size))


load_total_time = 0.0
process_total_time = 0.0
save_total_time = 0.0
df_list = []
#with zipfile.ZipFile(OUT_TRAIN, 'w') as img_out:
load_before = time.time()
for fname in TRAIN:
    print(fname, flush=True)
    df = pd.read_parquet(fname)
    df_list.append(df)
load_total_time = time.time()-load_before
# the input is inverted
process_before = time.time()
for df in df_list:
    data = 255 - df.values[:, 1:].reshape(-1, HEIGHT, WIDTH).astype(np.uint8)
    for idx in range(len(df)):
        #name = df.iloc[idx,0]
        # normalize each image by its max val
        # process_before=time.time()
        img = (data[idx]*(255.0/data[idx].max())).astype(np.uint8)
        img = crop_resize(img)
        img = cv2.imencode('.png', img)[1]
process_total_time = time.time()-process_before
# save_before=time.time()
#img_out.writestr(name + '.png', img)
# save_total_time+=time.time()-save_before
print(load_total_time)
print(process_total_time)
print(save_total_time)
json.dump({
    "load_time": load_total_time,
    "process_time": process_total_time,
    "save_time": save_total_time
}, open("./singleNodeNFS.json","w"), indent=4)
