from __future__ import division

from models import *
from utils.utils import *
from utils.datasets import *

import os
import sys
import time
import datetime
import argparse

from PIL import Image

import torch
from torch.utils.data import DataLoader
from torchvision import datasets
from torch.autograd import Variable

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.ticker import NullLocator
#93
if __name__ == "__main__":  #85
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_folder", type=str, default="data/samples", help="path to dataset")
    parser.add_argument("--model_def", type=str, default="config/custom.cfg", help="path to model definition file")
    parser.add_argument("--weights_path", type=str, default="checkpoints/yolov3_ckpt_46.pth", help="path to weights file")
    parser.add_argument("--class_path", type=str, default="data/custom/classes.names", help="path to class label file")
    parser.add_argument("--conf_thres", type=float, default=0.8, help="object confidence threshold")
    parser.add_argument("--nms_thres", type=float, default=0.2, help="iou thresshold for non-maximum suppression")
    parser.add_argument("--batch_size", type=int, default=1, help="size of the batches")
    parser.add_argument("--n_cpu", type=int, default=0, help="number of cpu threads to use during batch generation")
    parser.add_argument("--img_size", type=int, default=416, help="size of each image dimension")
    parser.add_argument("--checkpoint_model", type=str,default ='checkpoints/yolov3_ckpt_99.pth' , help="path to checkpoint model")
    opt = parser.parse_args()
    print(opt)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    os.makedirs("output", exist_ok=True)

    # Set up model
    model = Darknet(opt.model_def, img_size=opt.img_size).to(device)

    if opt.weights_path.endswith(".weights"):
        # Load darknet weights
        model.load_darknet_weights(opt.weights_path)
    else:
        # Load checkpoint weights
        model.load_state_dict(torch.load(opt.weights_path))

    model.eval()  # Set in evaluation mode

    dataloader = DataLoader(
        ImageFolder(opt.image_folder, img_size=opt.img_size),
        batch_size=opt.batch_size,
        shuffle=False,
        num_workers=opt.n_cpu,
    )

    classes = load_classes(opt.class_path)  # Extracts class labels from file
    print('classes is ', classes)
    Tensor = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor

    imgs = []  # Stores image paths
    img_detections = []  # Stores detections for each image index

    print("\nPerforming object detection:")
    prev_time = time.time()
    try:
        for batch_i, (img_paths, input_imgs) in enumerate(dataloader):
            # Configure input
            print('****')
            input_imgs = Variable(input_imgs.type(Tensor))
    
            # Get detections
            with torch.no_grad():
                detections = model(input_imgs)
                detections = non_max_suppression(detections, opt.conf_thres, opt.nms_thres)
    
            # Log progress
            current_time = time.time()
            inference_time = datetime.timedelta(seconds=current_time - prev_time)
            prev_time = current_time
            print("\t+ Batch %d, Inference Time: %s" % (batch_i, inference_time))
    
            # Save image and detections
            imgs.extend(img_paths)
            img_detections.extend(detections)
    except Exception as e:
        print(e)
        pass

    # Bounding-box colors
    cmap = plt.get_cmap("BuGn_r")
    colors = [cmap(i) for i in np.linspace(0, 1, 20)]
    i = 0
    print("\nSaving images:")
    # Iterate through images and save plot of detections
    for img_i, (path, detections) in enumerate(zip(imgs, img_detections)):
        start_time = time.time()
        print("(%d) Image: '%s'" % (img_i, path))

        # Create plot
        img = np.array(Image.open(path))
        plt.figure()
        fig, ax = plt.subplots(1)
        ax.imshow(img)
        
#        plt.savefig(str(i) +"filename.png")

        # Draw bounding boxes and labels of detections
        if detections is not None:
            # Rescale boxes to original image
            detections = rescale_boxes(detections, opt.img_size, img.shape[:2])
            unique_labels = detections[:, -1].cpu().unique()
#            print(detections)
            n_cls_preds = len(unique_labels)
            print('///', n_cls_preds)
            bbox_colors = random.sample(colors, n_cls_preds)
            try:
                for x1, y1, x2, y2, conf, cls_conf, cls_pred in detections:
#                    print('***********')
                    if cls_conf < 0.5:
                        continue
                    print('int(cls_pred)',int(cls_pred))
#                    if int(cls_pred) > 3:
#                        int(cls_pred) = 3
                    print("\t+ Label: %s, Conf: %.5f" % (classes[int(cls_pred) ], cls_conf.item()))
                    box_w = x2 - x1
                    box_h = y2 - y1
#                    print('/////////')
#                    if cls_pred < 0.4:
#                        continue
                    color = bbox_colors[int(np.where(unique_labels == int(cls_pred))[0])]
                    # Create a Rectangle patch
                    
                    bbox = patches.Rectangle((x1, y1), box_w, box_h, linewidth=2, edgecolor=color, facecolor="none")
                    # Add the bbox to the plot
                    ax.add_patch(bbox)
#                    print('+++++++++++')
                    # Add label
                    plt.text(
                        x1,
                        y1,
                        s=classes[int(cls_pred)] + str(round(cls_conf.item(),3)),
                        color="black",
                        verticalalignment="top",
                        bbox={"color": color, "pad": 0},
                    )
#                    print('end')
            except Exception as e:
                print(e)
                pass

        # Save generated image with detections
        plt.rcParams['figure.figsize'] = (20, 10.0)
        plt.axis("off")
        plt.gca().xaxis.set_major_locator(NullLocator())
        plt.gca().yaxis.set_major_locator(NullLocator())
        filename = path.split("/")[-1].split(".")[0]
        plt.savefig("./output/" + str(i) + "filename.png", bbox_inches="tight", pad_inches=0.0)
        end_time =  time.time() - start_time
        print('**********time is ', end_time)
        i += 1
        plt.close()


