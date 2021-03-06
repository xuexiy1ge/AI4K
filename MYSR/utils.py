import cv2
import numpy as np
import random
import torch.nn as nn
import torch


def get_file_name(file):
    # file = '/aaa/bbb/1050345\\050.png'  return /aaa/bbb/1050345 050
    file = file.replace('\\', '/')
    d_list = file.rsplit('/', maxsplit=1)
    path = d_list[0]
    file_text = d_list[-1]
    name = file_text.split('.')[0]
    return path, name

def horizontal_flip(image, axis):
    if axis != 2:
        image = cv2.flip(image, axis)
    return image

def augment(img_list, hflip=True, rot=True):
    """horizontal flip OR rotate (0, 90, 180, 270 degrees)"""
    hflip = hflip and random.random() < 0.5
    vflip = rot and random.random() < 0.5
    rot90 = rot and random.random() < 0.5

    def _augment(img):
        if hflip:
            img = img[:, ::-1, :]
        if vflip:
            img = img[::-1, :, :]
        if rot90:
            img = img.transpose(1, 0, 2)
        return img

    return [_augment(img) for img in img_list]

def read_img(path):
    """read image by cv2
    return: Numpy float32, HWC, RGB, [0,1]"""
    img = cv2.imread(path) #BGR
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.
    return img


def getFileName(lr_file):
    # lr_file = '/aaa/bbb/1050345\\050.png'
    lr_file = lr_file.replace('\\', '/')

    file_name = lr_file.split('/')[-1]
    name = file_name.split('.')[0]

    x = int(name)
    b = x - 1 if x != 1 else x + 1
    f = x + 1 if x != 100 else x - 1

    b_file = lr_file.replace(file_name, '%03d.png' % b)
    f_file = lr_file.replace(file_name, '%03d.png' % f)

    return  b_file,f_file

class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def psnr_cal_0_255(pred, gt):
    batch = pred.shape[0]
    psnr = 0
    for i in range(batch):
        pr = pred[i]
        hd = gt[i]
        mse = np.mean((pr / 1. - hd / 1.) ** 2)
        if mse < 1.0e-10:
            psnr = psnr + 45
            continue
        psnr = psnr + 10 * np.log10(255 * 255 / mse)
    return psnr / (batch)

def psnr_cal_0_255_YCrCb2RGB(pred, gt):
    batch = pred.shape[0]
    psnr = 0
    for i in range(batch):
        pr = pred[i]
        hd = gt[i]
        pr = cv2.cvtColor(np.transpose(pr, (1, 2, 0)), cv2.COLOR_YCrCb2RGB)
        hd = cv2.cvtColor(np.transpose(hd, (1, 2, 0)), cv2.COLOR_YCrCb2RGB)
        pr = np.transpose(pr, (2, 0, 1))
        hd = np.transpose(hd, (2, 0, 1))

        mse = np.mean((pr / 1. - hd / 1.) ** 2)
        if mse < 1.0e-10:
            psnr = psnr + 45
            continue
        psnr = psnr + 10 * np.log10(255 * 255 / mse)
    return psnr / (batch)

def psnr_cal_0_1(pred, gt):
    batch = pred.shape[0]
    psnr = 0
    for i in range(batch):
        pr = pred[i]
        hd = gt[i]
        mse = np.mean((pr / 1. - hd / 1.) ** 2)
        psnr = psnr + 10* np.log10(1. / mse)
    return psnr / (batch)

def SSIMnp(pred, gt):
    batch = pred.shape[0]
    all = 0.
    for i in range(batch):
        y_true, y_pred = pred[i],gt[i]
        u_true,u_pred = np.mean(y_true),np.mean(y_pred)
        var_true,var_pred = np.var(y_true),np.var(y_pred)
        std_true,std_pred = np.sqrt(var_true),np.sqrt(var_pred)
        c1,c2  = np.square(0.01*7), np.square(0.03*7)
        ssim = (2 * u_true * u_pred + c1) * (2 * std_pred * std_true + c2)
        denom = (u_true ** 2 + u_pred ** 2 + c1) * (var_pred + var_true + c2)
        all = all +  ssim / denom
    return all / (batch)

class MeanShift(nn.Conv2d):
    def __init__(self, rgb_range=255, rgb_mean=(0.4488, 0.4371, 0.4040), rgb_std=(1.0, 1.0, 1.0), sign=-1):
        super(MeanShift, self).__init__(3, 3, kernel_size=1)
        std = torch.Tensor(rgb_std)
        self.weight.data = torch.eye(3).view(3, 3, 1, 1) / std.view(3, 1, 1, 1) #
        self.bias.data = sign * rgb_range * torch.Tensor(rgb_mean) / std
        for p in self.parameters():
            p.requires_grad = False