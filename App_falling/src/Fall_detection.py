import torch
import cv2
import math
from torchvision import transforms
import numpy as np
import os

from tqdm import tqdm

from utils.datasets import letterbox
# non-maximum suppression: filter out the low confidence detections
from utils.general import non_max_suppression_kpt
# keypoint plotting functions
from utils.plots import output_to_keypoint, plot_skeleton_kpts

class FallDetector(object):
    def __init__(self, path_model, device):
        self.path_model = path_model
        self.device = torch.device(device)
        self.model = self.load_model(self.path_model)
        

    def load_model(self, path_model):
        # load model weights
        weights = torch.load(path_model, map_location=self.device, weights_only=False)
        model = weights['model']
        # .float() to convert the model to float32(inference requires 32-bit precision)
        # .eval() to set the model to evaluation mode
        _ = model.float().eval()
        # if GPU is available, convert the model to half precision and assign it to the device(GPU)
        if torch.cuda.is_available():
            model = model.half().to(self.device)
        print("YOLOv7 model loaded")
        return model
    
    # inference function, controls the entire inference process
    def inference(self, image):
        image_raw = image.copy()
        # get the resized image and the output(keypoints)
        img, output = self.get_pose(image)
        # prepare the image for the display (convert to BGR(opencv default) format)
        img_pre = self.prepare_image(img)
        # fall detection algorithm
        is_fall, bbox = self.fall_detection(output)
        # if fall is detected, draw the bounding box on the image
        if is_fall:
            # scale the coordinates of the bounding box to the original image size
            bbox_raw = self.scale_coords(img_pre.shape, np.array([bbox]), image.shape).round()
            # draw the bounding box on the image
            img_result = self.falling_alarm(image_raw, bbox_raw)
        else:
            # if fall is not detected, return the original image
            img_result = image_raw
        return img_result, is_fall
    
    # draw the bounding box on the image
    def falling_alarm(self, image, bboxes):
        for box in bboxes:
            cv2.rectangle(image, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color=(0, 0, 255),
                        thickness=5, lineType=cv2.LINE_AA)
        return image
    
    def get_pose(self, image):
        # letterbox: resize the image to the target size(640x640) while maintaining the aspect ratio
        image = letterbox(image, 640, stride=64, auto=True)[0]
        image = transforms.ToTensor()(image)
        image = torch.tensor(np.array([image.numpy()]))
        if torch.cuda.is_available():
            image = image.half().to(self.device)
        with torch.no_grad():
            # forward pass: pass the image through the model to get the output(first layer object detection)
            output, _ = self.model(image)

        # filter out the low confidence detections(good for reducing false positives or reducing any other detections)
        output = non_max_suppression_kpt(output, 0.25, 0.65, nc=self.model.yaml['nc'], nkpt=self.model.yaml['nkpt'],
                                        kpt_label=True)
        with torch.no_grad():
            # keypoint detection
            output = output_to_keypoint(output)

        # return the image and the output(keypoints)
        return image, output
    
    # translate to opencv readable format(convert to BGR(opencv default) format)
    def prepare_image(self, image):
        _img = image[0].permute(1, 2, 0) * 255
        _img = _img.cpu().numpy().astype(np.uint8)
        _img = cv2.cvtColor(_img, cv2.COLOR_BGR2RGB)
        img = cv2.cvtColor(_img, cv2.COLOR_RGB2BGR)
        return img
    
    # scale the coordinates of the bounding box to the original image size
    def scale_coords(self, img1_shape, coords, img0_shape, ratio_pad=None):
        if ratio_pad is None:  # calculate from img0_shape
            gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])  # gain  = old / new
            pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (img1_shape[0] - img0_shape[0] * gain) / 2  # wh padding
        else:
            gain = ratio_pad[0][0]
            pad = ratio_pad[1]
        coords[:, [0, 2]] -= pad[0]  # x padding
        coords[:, [1, 3]] -= pad[1]  # y padding
        coords[:, :4] /= gain
        self.clip_coords(coords, img0_shape)
        return coords

    # clip the coordinates of the bounding box to the image size(checking if the coordinates are within the image boundaries)
    def clip_coords(self, boxes, shape):
        if isinstance(boxes, torch.Tensor): 
            boxes[:, 0].clamp_(0, shape[1])  # x1
            boxes[:, 1].clamp_(0, shape[0])  # y1
            boxes[:, 2].clamp_(0, shape[1])  # x2
            boxes[:, 3].clamp_(0, shape[0])  # y2
        else:
            boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, shape[1])  # x1, x2
            boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, shape[0])  # y1, y2

    # fall detection algorithm
    def fall_detection(self, poses):
        for pose in poses:
            xmin, ymin = (pose[2] - pose[4] / 2), (pose[3] - pose[5] / 2)
            xmax, ymax = (pose[2] + pose[4] / 2), (pose[3] + pose[5] / 2)
            left_shoulder_y = pose[23]
            left_shoulder_x = pose[22]
            right_shoulder_y = pose[26]
            left_body_y = pose[41]
            left_body_x = pose[40]
            right_body_y = pose[44]
            len_factor = math.sqrt(((left_shoulder_y - left_body_y) ** 2 + (left_shoulder_x - left_body_x) ** 2))
            left_foot_y = pose[53]
            right_foot_y = pose[56]
            dx = int(xmax) - int(xmin)
            dy = int(ymax) - int(ymin)
            difference = dy - dx
            if left_shoulder_y > left_foot_y - len_factor and left_body_y > left_foot_y - (
                    len_factor / 2) and left_shoulder_y > left_body_y - (len_factor / 2) or (
                    right_shoulder_y > right_foot_y - len_factor and right_body_y > right_foot_y - (
                    len_factor / 2) and right_shoulder_y > right_body_y - (len_factor / 2)) \
                    or difference < 0:
                return True, [xmin, ymin, xmax, ymax]
        return False, []
