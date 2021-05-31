from kornia.augmentation.augmentation import Denormalize, CenterCrop, RandomGaussianNoise, ColorJitter, GaussianBlur, RandomRotation, RandomSolarize, RandomEqualize, Normalize
from matplotlib import image
from numpy.lib.type_check import imag
import torch
import torch.utils.data as data
import data_loader
import argparse
import os
import model
import matplotlib.pyplot as plt
import numpy as np
from custom_activations import HardELU
from plotting import plot_history, save_batch
from datetime import date
from losses import loss
from functools import partial
from torchvision.utils import make_grid

is_cuda = torch.cuda.is_available()

clr_jitter = ColorJitter(0.1, 0.1, 0.1, 0.1, p=.371)
blur = GaussianBlur(kernel_size=(3,9), sigma=(.5, 1), p=.25)
rgs = RandomGaussianNoise(p=0.25, std=0.1)
normalize = Normalize(torch.from_numpy(np.array([0.485, 0.456, 0.406])), torch.from_numpy(np.array([0.229, 0.224, 0.225])))
denormalize = Denormalize(torch.from_numpy(np.array([0.485, 0.456, 0.406])), torch.from_numpy(np.array([0.229, 0.224, 0.225])))
rotation = RandomRotation((-15, 15), return_transform=True)
crop1 = CenterCrop(480)
def transform_data(image_batch, mask_batch):
    image_batch = clr_jitter(image_batch)
    image_batch = blur(image_batch)
    image_batch = rgs(image_batch)
    image_batch = normalize(image_batch)
    image_batch = crop1(image_batch)
    mask_batch = crop1(mask_batch)
    return image_batch, mask_batch



def load_ds(ds_dir, load_memory, batch_size=9):
    ds = data_loader.ObjectSegmentationDataset(ds_dir=ds_dir, annotation_path=os.path.join(ds_dir, "annotations.json"), load_memory=load_memory) if ds_dir else None
    if ds: return data.DataLoader(ds, batch_size=batch_size, num_workers=4, pin_memory=True, drop_last=True)
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("option", default="train", type=str, help="train/test/both")
    parser.add_argument("-train_ds", default=None, type=str)
    parser.add_argument("-test_ds", default=None, type=str)
    parser.add_argument("-valid_ds", default=None, type=str)
    parser.add_argument("-figure_dir", default="./figs", type=str)
    parser.add_argument("-lr", default=0.001, type=float)
    parser.add_argument("-loss_fn", default="bce_dice", type=str)
    parser.add_argument("-epochs", default=10, type=int)
    parser.add_argument("-batch_size", default=9, type=int)
    parser.add_argument("-load_memory", action="store_true")
    args = parser.parse_args()

    option = args.option
    print(f"Loading data...")
    load_ds = partial(load_ds, load_memory=args.load_memory, batch_size=args.batch_size)
    train_loader = load_ds(args.train_ds)
    test_loader = load_ds(args.test_ds)
    valid_loader = load_ds(args.valid_ds)
    print(f"Data loaded.")

    net = model.Segmentator(activation_function=HardELU)
    net = net.cuda()
    net.loss_fn = loss[args.loss_fn]
    
    optimizer = torch.optim.Adam(net.parameters(), lr=args.lr)
    print("Starting program.")
    figure_dir = os.path.join(args.figure_dir, date.today().strftime("%Y-%m-%d"))
    if not os.path.exists(figure_dir): os.makedirs(figure_dir)
    if option == "train":
        EPOCH = 1
        train_losses, train_ious, valid_losses, valid_ious = [], [], [], []
        for metrics in net.train_and_validate(train_loader, valid_loader, args.epochs, optimizer=optimizer, transform_data=transform_data, denormalizer=denormalize):
            estimate_masked, train_loss, train_iou, valid_loss, valid_iou = metrics
            save_batch(estimate_masked, os.path.join(figure_dir, f"estimates-{EPOCH}.png"))
            train_losses.append(train_loss)
            train_ious.append(train_iou)
            valid_losses.append(valid_loss)
            valid_ious.append(valid_iou)
            EPOCH += 1
        fig = plot_history({"train_loss": train_losses, "train_iou": train_ious, "valid_loss": valid_losses, "valid_iou": valid_ious})
        fig.savefig(os.path.join(figure_dir, "output_figure.pdf"))
        plt.close(fig)
        torch.save(net.state_dict(), os.path.join(figure_dir, "model.pth"))
    else: print(f"{option} not implemented yet")
    