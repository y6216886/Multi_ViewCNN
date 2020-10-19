import os
from PIL import Image
import torch.utils.data as data
import torch
import torchvision.transforms as transforms
from torchvision.models import resnet18
import torch.nn as nn
import torchvision.models as models
import pandas as pd
import numpy as np
import random
import glob

def pil_loader(path):
    return Image.open(path).convert("RGB")


def get_label(label_dir):
    label_df = pd.read_csv(label_dir)
    label_df = label_df.set_index('details')
    return label_df

def make_dataset_before(rootpath, root, label_df):
    images_light = []
    images_dark = []
    for line in open (root):
        org_path = line.strip ('\n')
        labelsyne = label_df.loc[org_path, "synechia"]
        """
        尝试一下分类宽窄角
        """
        # labelopennarrow = label_df.loc[org_path, "openORnarrow"]
        label =  labelsyne ###sysnechia
        #####
        eyeid = org_path.split ("_")[0]
        odos = org_path.split ("_")[1]
        region = org_path.split ("_")[2]
        indexs = int (org_path.split ("_")[3])
        realpath = rootpath + "/" + eyeid + "/"
        if odos == "od":
            realpath += "R"
        elif odos == "os":
            realpath += "L"
        darkrealpath = realpath + "/D/"
        lightrealpath = realpath + "/L/"
        lightrealpath += str (int (indexs / 2))
        darkrealpath += str (int (indexs / 2))
        if region =="left":
            vertical_light = int(np.load(lightrealpath + "/vertical_l.npy"))
            vertical_dark = int(np.load(darkrealpath + "/vertical_l.npy"))
        if region =="right":
            vertical_light = int(np.load(lightrealpath + "/vertical_r.npy"))
            vertical_dark = int(np.load(darkrealpath + "/vertical_r.npy"))
        all_image_path = list (os.listdir (lightrealpath))
        all_image_path.sort ()
        if indexs / 2 - int (indexs / 2) == 0.5:
            images_light.append ((all_image_path[11:21], lightrealpath, label, region, vertical_light))
            all_image_path1 = list (os.listdir (darkrealpath))
            all_image_path1.sort ()
            images_dark.append ((all_image_path1[11:21], darkrealpath, label, region, vertical_dark))
        if indexs / 2 - int (indexs / 2) == 0:
            images_light.append ((all_image_path[1:11], lightrealpath, label, region, vertical_light))
            all_image_path1 = list (os.listdir (darkrealpath))
            all_image_path1.sort ()
            images_dark.append ((all_image_path1[1:11], darkrealpath, label, region, vertical_dark))
    # print(images_dark)
    return images_light, images_dark



def gethalf(realpath, indexs, region):
    res = {}
    realpath += str(int(indexs / 2))
    if region == "left":
        vertical = int(np.load(realpath + "/vertical_l.npy"))
    if region == "right":
        vertical = int(np.load(realpath + "/vertical_r.npy"))
    # all_image_path = list(os.listdir(realpath))
    all_image_path = glob.glob(os.path.join(realpath, "*.png"))
    all_image_path.sort()
    if indexs / 2 - int(indexs / 2) == 0.5:
        # images_light.append((all_image_path[11:21], lightrealpath, label, region, vertical_light))
        res["imagelist"] = all_image_path[11:21]
        res["vertical"] = vertical
        res["region"] = region
    if indexs / 2 - int(indexs / 2) == 0:
        # images_light.append((all_image_path[1:11], lightrealpath, label, region, vertical_light))
        res["imagelist"] = all_image_path[1:11]
        res["vertical"] = vertical
        res["region"] = region
    return res

def make_dataset(rootpath, root, label_df):
    images_light = []
    images_dark = []
    for line in open (root):
        org_path = line.strip ('\n')
        label = label_df.loc[org_path, "synechia"]
        eyeid = org_path.split ("_")[0]
        region = org_path.split ("_")[1]
        indexs = org_path.split ("_")[2]
        realpath = rootpath + "/" + eyeid + "/"
        realpath = glob.glob(os.path.join(realpath,"*"))[0]
        print(realpath)
        darkrealpath = realpath + "/D/"
        lightrealpath = realpath + "/L/"
        res_d = gethalf(darkrealpath, int(indexs), region)
        res_l = gethalf(lightrealpath, int(indexs), region)
        res_l["label"] = label
        res_l["details"] = org_path
        res_d["label"] = label
        res_d["details"] = org_path
        images_light.append(res_l)
        images_dark.append(res_d)

    return images_light, images_dark

def make3d(dicts, transform):   ##dict   {"imagelist_half1":imagelist1, "vertical_half1":vertical_half1, "region_half1":region_half1,,,half2,,,,"lalel":label,"details":CS-001_od_left_1}
    imgs = Image.open(dicts["imagelist"][0]).convert("RGB")
    lists = dicts["imagelist"]
    label = dicts["label"]
    region = dicts["region"]
    regionCor_l = (0, 0, imgs.size[0] / 2, imgs.size[1])
    regionCor_r = (imgs.size[0] / 2, 0, imgs.size[0], imgs.size[1])
    vertical_center = dicts["vertical"]
    vrc = VerticalCrop(244)
    rgc = RandomGammaCorrection()
    rgc.randomize_parameters()
    imglist = []
    fullimglist = []
    details = dicts["details"]
    if region=="right":
        regionCor = regionCor_r
    elif region=="left":
        regionCor = regionCor_l
    for imgpath in lists:
        fullimg = Image.open(imgpath).convert("RGB")
        orgimage = fullimg.crop(regionCor)
        vrc.randomize_parameters(vertical_center)
        crop_image = np.asarray(vrc(orgimage))
        crop_image = np.asarray(rgc(crop_image))
        img = Image.fromarray(crop_image, 'RGB')
        if region == "right":
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
            img.save('/home/yangyifan/save/crop_RU.jpg')
        imglist.append(transform(img))
        fullimglist.append(transform(fullimg))

    input = torch.stack (imglist).permute(1, 0, 2, 3)
    fullinput = torch.stack (fullimglist).permute(1, 0, 2, 3)
    return input, label, fullinput, details

class Myloader(data.Dataset):
    def __init__(self, rootpath, txtroot, label_dir, transform=None):  ##root: path before filename
        self.root = txtroot
        self.label_dir = label_dir
        self.loader = pil_loader
        self.transform = transform
        self.label_df = get_label(label_dir)
        self.rootpath = rootpath
        self.images_light, self.images_dark = make_dataset(rootpath, txtroot, self.label_df)


    def __getitem__(self, index):
        images_light = self.images_light[index]
        images_dark = self.images_dark[index]
        dark_input, label, dark_full_input, details = make3d(images_dark,   self.transform)
        light_input, label, light_full_input, details = make3d (images_light,   self.transform)
        return (dark_input, dark_full_input), (light_input, light_full_input), label, details

    def __len__(self):
        return len (self.images_light)



class RandomGammaCorrection():
    def __init__(self):
        self.gamma = 1.0

    def __call__(self, img):
        img = np.asarray(img)
        img = np.power(img / 255.0, self.gamma)
        img = np.uint8(img * 255.0)

        return Image.fromarray(img)


    def randomize_parameters(self, custom_extend=None):
        self.gamma = np.random.uniform(1, 2, 1)
        if random.random() < 0.5:
            self.gamma = 1 / self.gamma

class VerticalCrop(object):

    def __init__(self, size, interpolation=Image.BILINEAR):
        self.size = size
        self.interpolation = interpolation
        self.vertical_center = None
        self.ratio = 0.05
        self.hwr = 1.2

    def __call__(self, img):
        image_width = img.size[0]
        image_height = img.size[1]
        vertical_center = self.vertical_center + int(self.ratio * image_width)
        crop_height = image_width * self.hwr
        if vertical_center - crop_height // 2 < 0:
            x1 = 0
            y1 = 0
            x2 = image_width
            y2 = crop_height
        elif vertical_center + crop_height // 2 > image_height:
            x1 = 0
            y1 = image_height - crop_height
            x2 = image_width
            y2 = image_height
        else:
            x1 = 0
            y1 = vertical_center - crop_height // 2
            x2 = image_width
            y2 = vertical_center + crop_height // 2

        img = img.crop((x1, y1, x2, y2))

        return img.resize((self.size, self.size), self.interpolation)

    def randomize_parameters(self, vertical_center):
        """
        custom_extend: vertical center coordinate for estimated spur sceleral position.
        """
        self.vertical_center = vertical_center

class RandomVerticalCrop(object):

    def __init__(self, size,interpolation=Image.BILINEAR):
        self.size = size
        self.interpolation = interpolation
        self.vertical_center = None
        self.ratio = 0.05
        self.hwr = 1.2

    def __call__(self, img):
        image_width = img.size[0]
        image_height = img.size[1]
        vertical_center = self.vertical_center + int(self.ratio * image_width)
        crop_height = image_width * self.hwr
        if vertical_center - crop_height // 2 < 0:
            x1 = 0
            y1 = 0
            x2 = image_width
            y2 = crop_height
        elif vertical_center + crop_height // 2 > image_height:
            x1 = 0
            y1 = image_height - crop_height
            x2 = image_width
            y2 = image_height
        else:
            x1 = 0
            y1 = vertical_center - crop_height // 2
            x2 = image_width
            y2 = vertical_center + crop_height // 2

        img = img.crop((x1, y1, x2, y2))

        return img.resize((self.size, self.size), self.interpolation)