import argparse
import os
import numpy as np
import torch
from PIL import Image
from torch.autograd import Variable
from torchvision.transforms import ToTensor
from tqdm import tqdm

from ESPCN_Pytorch.data_utils import is_image_file
from ESPCN_Pytorch.model import Net

def test_one():
    UPSCALE_FACTOR = 4
    MODEL_NAME = 'epochs/epoch_99_.pth'
    src_file = 'J:/test/one_L.png'
    dst_file = 'J:/test/one_SR.png'
    bicubic_file = 'J:/test/one_bicubic.png'
    model = Net(upscale_factor=UPSCALE_FACTOR)
    if torch.cuda.is_available():
        model = model.cuda()
    model.load_state_dict(torch.load(MODEL_NAME))
    model.eval()


    img = Image.open(src_file)
    bicubic = img.resize((img.width*UPSCALE_FACTOR, img.height*UPSCALE_FACTOR), Image.BICUBIC)
    bicubic.save(bicubic_file)

    img = img.convert('YCbCr')
    y, cb, cr = img.split()
    image = Variable(ToTensor()(y)).view(1, -1, y.size[1], y.size[0])
    if torch.cuda.is_available():
        image = image.cuda()

    out = model(image)
    out = out.cpu()
    out_img_y = out.data[0].numpy()
    out_img_y *= 255.0
    out_img_y = out_img_y.clip(0, 255)
    out_img_y = Image.fromarray(np.uint8(out_img_y[0]), mode='L')
    out_img_cb = cb.resize(out_img_y.size, Image.BICUBIC)
    out_img_cr = cr.resize(out_img_y.size, Image.BICUBIC)
    out_img = Image.merge('YCbCr', [out_img_y, out_img_cb, out_img_cr]).convert('RGB')
    out_img.save(dst_file)

def word():
    UPSCALE_FACTOR = 4
    MODEL_NAME = 'epochs/epoch_99_.pth'
    image_path = 'J:/img_L'
    out_path = 'J:/img_H'
    model = Net(upscale_factor=UPSCALE_FACTOR)
    if torch.cuda.is_available():
        model = model.cuda()
    model.load_state_dict(torch.load(MODEL_NAME))
    model.eval()

    images_name = [x for x in os.listdir(image_path)]
    for image_name in tqdm(images_name, desc='convert LR images to HR images'):
        src_file = os.path.join(image_path,image_name)
        dst_file = os.path.join(out_path,image_name)

        img = Image.open(src_file).convert('YCbCr')
        y, cb, cr = img.split()
        image = Variable(ToTensor()(y)).view(1, -1, y.size[1], y.size[0])
        if torch.cuda.is_available():
            image = image.cuda()

        out = model(image)
        out = out.cpu()
        out_img_y = out.data[0].numpy()
        out_img_y *= 255.0
        out_img_y = out_img_y.clip(0, 255)
        out_img_y = Image.fromarray(np.uint8(out_img_y[0]), mode='L')
        out_img_cb = cb.resize(out_img_y.size, Image.BICUBIC)
        out_img_cr = cr.resize(out_img_y.size, Image.BICUBIC)
        out_img = Image.merge('YCbCr', [out_img_y, out_img_cb, out_img_cr]).convert('RGB')
        out_img.save(dst_file)

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='Test Super Resolution')
    # parser.add_argument('--upscale_factor', default=3, type=int, help='super resolution upscale factor')
    # parser.add_argument('--model_name', default='epoch_3_100.pt', type=str, help='super resolution model name')
    # opt = parser.parse_args()
    # UPSCALE_FACTOR = opt.upscale_factor
    # MODEL_NAME = opt.model_name


    # test_one()
    word()

