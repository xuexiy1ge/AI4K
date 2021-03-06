import argparse
import os
from glob import glob
import numpy as np
import torch
from tqdm import tqdm
import torch.backends.cudnn as cudnn
from collections import OrderedDict
import torch.optim as optim
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.autograd import Variable

from model.rcan import RCAN
from dataloder import  DatasetLoader
from utils import  AverageMeter,psnr_cal
import sys
import time


def one_epoch_train_tqdm(model,optimizer,criterion,data_len,train_loader,epoch,epochs,batch_size,lr):
    model.train()
    losses = AverageMeter()
    psnrs = AverageMeter()
    with tqdm(total=(data_len -  data_len%batch_size)) as t:
        t.set_description('epoch:{}/{} lr={}'.format(epoch, epochs - 1, lr))

        for data in train_loader:
            # data_x, data_y = Variable(data[0]), Variable(data[1], requires_grad=False)
            # data_x = data_x.type(torch.FloatTensor)
            # data_y = data_y.type(torch.FloatTensor)

            data_x = data[0].cuda()
            data_y = data[1].cuda()

            pred = model(data_x)
            # pix loss
            loss = criterion(pred, data_y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            pred = pred.cpu()
            pred = pred.detach().numpy().astype(np.float32)

            data_y = data_y.cpu()
            data_y = data_y.numpy().astype(np.float32)

            psnr = psnr_cal(pred, data_y)
            mean_loss = loss.item() / (args.batch_size * args.n_colors * ((args.patch_size * args.scale) ** 2))
            losses.update(mean_loss)
            psnrs.update(psnr)

            t.set_postfix(loss='Loss: {losses.val:.3f} ({losses.avg:.3f})'
                               ' PNSR: {psnrs.val:.3f} ({psnrs.avg:.3f})'
                          .format(losses=losses, psnrs=psnrs))

            t.update(batch_size)
    return losses, psnrs

def one_epoch_train_logger(model,optimizer,criterion,data_len,train_loader,epoch,epochs,batch_size,lr):
    model.train()
    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    psnrs = AverageMeter()

    end = time.time()
    for iteration, data in enumerate(train_loader):
        data_time.update(time.time() - end)

        # data_x, data_y = Variable(data[0]), Variable(data[1], requires_grad=False)
        # data_x = data_x.type(torch.FloatTensor)
        # data_y = data_y.type(torch.FloatTensor)

        data_x = data[0].cuda()
        data_y = data[1].cuda()

        pred = model(data_x)
        # pix loss
        loss = criterion(pred, data_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        pred = pred.cpu()
        pred = pred.detach().numpy().astype(np.float32)
        data_y = data_y.cpu()
        data_y = data_y.numpy().astype(np.float32)
        psnr = psnr_cal(pred, data_y)
        mean_loss = loss.item() / (args.batch_size * args.n_colors * ((args.patch_size * args.scale) ** 2))

        losses.update(mean_loss)
        psnrs.update(psnr)
        batch_time.update(time.time() - end)

        end = time.time()
        use_time = batch_time.sum
        time_h = use_time//3600
        time_m = (use_time-time_h*3600)//60
        show_time =  '%d:%d:%d'%(time_h,time_m,use_time%60)

        if iteration % args.print_freq == 0:
            print('Epoch:[{0}/{1}][{2}/{3}]  lr={4}\t {5} \t'
                  'data_time: {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'batch_time: {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Loss: {losses.val:.3f} ({losses.avg:.3f})\t'
                  'PNSR: {psnrs.val:.3f} ({psnrs.avg:.3f})'
                  .format(epoch, epochs, iteration, data_len // batch_size, lr, show_time,
                          data_time=data_time,batch_time=batch_time,  losses=losses, psnrs=psnrs))
            sys.stdout.flush()
    return losses,psnrs

def main(args):
    print("===> Loading datasets")
    file_name = sorted(os.listdir(args.data_lr))
    lr_list = []
    hr_list = []
    for one in file_name:
        lr_tmp = sorted( glob(os.path.join(args.data_lr, one,'*.png')) )
        lr_list.extend(lr_tmp)
        hr_tmp = sorted( glob(os.path.join(args.data_hr, one,'*.png')) )
        if len(hr_tmp) != 100:
            print(one)
        hr_list.extend(hr_tmp)


    # lr_list = glob(os.path.join(args.data_lr, '*'))
    # hr_list = glob(os.path.join(args.data_hr, '*'))

    data_set = DatasetLoader(lr_list, hr_list, args.patch_size, args.scale)
    data_len = len(data_set)
    train_loader = DataLoader(data_set, batch_size=args.batch_size, num_workers=args.workers, shuffle=True,
                              pin_memory=True, drop_last=True)


    print("===> Building model")
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)
    cudnn.benchmark = True

    model = RCAN(args)
    criterion = nn.L1Loss(reduction='sum')

    print("===> Setting GPU")
    gups = args.gpus if args.gpus != 0 else torch.cuda.device_count()
    device_ids = list(range(gups))
    model = nn.DataParallel(model, device_ids=device_ids)
    model = model.cuda()
    criterion = criterion.cuda()

    start_epoch = args.start_epoch
    # optionally resume from a checkpoint
    if args.resume:
        if os.path.isdir(args.resume):
            # 获取目录中最后一个
            pth_list = sorted(glob(os.path.join(args.resume, '*.pth')))
            if len(pth_list) > 0:
                args.resume = pth_list[-1]
        if os.path.isfile(args.resume):
            print("=> loading checkpoint '{}'".format(args.resume))
            checkpoint = torch.load(args.resume)

            start_epoch = checkpoint['epoch'] + 1
            state_dict = checkpoint['state_dict']

            new_state_dict = OrderedDict()
            for k, v in state_dict.items():
                namekey = 'module.' + k  # remove `module.`
                new_state_dict[namekey] = v
            model.load_state_dict(new_state_dict)
            # 如果文件中有lr，则不用启动参数
            args.lr = checkpoint.get('lr', args.lr)
        # 如果设置了 start_epoch 则不用checkpoint中的epoch参数
        start_epoch = args.start_epoch if args.start_epoch != 0 else start_epoch
    #如果use_current_lr大于0 测代替作为lr
    args.lr = args.use_current_lr if args.use_current_lr > 0 else args.lr

    print("===> Setting Optimizer")
    optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()),
                           lr=args.lr, weight_decay=args.weight_decay, betas=(0.9, 0.999), eps=1e-08)

    print("===> Training")
    for epoch in range(start_epoch, args.epochs):
        adjust_lr(optimizer, epoch)
        if args.use_tqdm == 1:
            losses, psnrs = one_epoch_train_tqdm(model, optimizer, criterion, data_len, train_loader, epoch,args.epochs, args.batch_size, optimizer.param_groups[0]["lr"])
        else:
            losses, psnrs = one_epoch_train_logger(model, optimizer, criterion, data_len, train_loader, epoch, args.epochs, args.batch_size, optimizer.param_groups[0]["lr"])

        # save model
        model_out_path = os.path.join(args.checkpoint,"model_epoch_%04d_rcan_loss_%.3f_psnr_%.3f.pth"%(epoch,losses.avg,psnrs.avg) )
        if not os.path.exists(args.checkpoint):
            os.makedirs(args.checkpoint)
        torch.save({
            'state_dict': model.module.state_dict(),
            "epoch": epoch,
            'lr':optimizer.param_groups[0]["lr"]
        }, model_out_path)





def adjust_lr(opt, epoch):
    scale = 0.1
    # if epoch in [200, 300, 350]:
    if epoch in [20, 30, 35]:
        args.lr *= scale
        print('Change lr to {}'.format(args.lr))
        for param_group in opt.param_groups:
            param_group['lr'] = param_group['lr'] * scale


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # model parameter
    parser.add_argument('--scale', default=4, type=int)
    parser.add_argument('--patch_size', default=128, type=int)
    parser.add_argument('--batch_size', default=7, type=int)
    parser.add_argument('--workers', default=14, type=int)
    parser.add_argument('--gpus', type=int, default=0)
    parser.add_argument('--seed', default=123, type=int)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--use_current_lr', type=float, default=-1)
    parser.add_argument('--weight_decay', type=float, default=1e-4)
    parser.add_argument("--start_epoch", default=0, type=int)
    parser.add_argument('--epochs', type=int, default=40)
    parser.add_argument("--n_res_blocks", type=int, default=20)
    parser.add_argument("--n_feats", type=int, default=64)
    parser.add_argument("--step", type=int, default=2)
    parser.add_argument('--n_colors', type=int, default=3,
                        help='number of color channels to use')
    parser.add_argument('--res_scale', type=float, default=0.1,
                        help='residual scaling')
    parser.add_argument('--rgb_range', type=int, default=255,
                        help='maximum value of RGB')
    parser.add_argument('--n_resgroups', type=int, default=12,
                        help='number of residual groups')
    parser.add_argument('--reduction', type=int, default=16,
                        help='number of feature maps reduction')

    # path
    parser.add_argument('--data-lr', type=str, metavar='PATH',default='train_lr')
    parser.add_argument('--data-hr', type=str, metavar='PATH',default='train_hr')

    # check point
    parser.add_argument("--resume", default='checkpoint', type=str)
    parser.add_argument("--checkpoint", default='checkpoint', type=str)
    parser.add_argument('--print_freq', default=100, type=int)
    parser.add_argument('--use_tqdm', default=0, type=int)
    args = parser.parse_args()
    main(args)

    # nohup python3 train.py>> output.log 2>&1 &
    # ps -aux|grep train.py
    # pgrep python3 | xargs kill -s 9

    #python3 train.py

    #python3 train.py  --batch_size 32 --use_tqdm 1

    #python train.py --data-lr J:/AI+4K/pngs/X4 --data-hr J:/AI+4K/pngs/gt --batch_size 4 --workers 4 --epochs 40


    # nvidia-smi
