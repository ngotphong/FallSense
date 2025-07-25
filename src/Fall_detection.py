# Import necessary libraries
import torch                     # PyTorch for deep learning
import cv2                       # OpenCV for image processing
import math                      # Math operations
from torchvision import transforms  # Image transformations
import numpy as np               # Numerical operations
import os                        # Operating system functions

from tqdm import tqdm            # Progress bar

# Import custom utility functions from the project
from utils.datasets import letterbox  # Resizes image while maintaining aspect ratio
# Non-maximum suppression: filter out overlapping detections with lower confidence
from utils.general import non_max_suppression_kpt
# Functions for keypoint extraction and visualization
from utils.plots import output_to_keypoint, plot_skeleton_kpts

class FallDetector(object):
    def __init__(self, path_model, device, show_keypoints=False):
        # Store the path to the model weights file
        self.path_model = path_model
        # Set up the device (CPU or GPU) for inference
        self.device = torch.device(device)
        # Load the YOLOv7 pose detection model
        self.model = self.load_model(self.path_model)
        # Flag to control whether keypoints are displayed
        self.show_keypoints = show_keypoints
        # Factor to adjust keypoint y-position (moves keypoints down to align with person)
        self.y_offset_factor = 0.35  # Adjusted value for best alignment
        
    def load_model(self, path_model):
        # Load model weights from file
        weights = torch.load(path_model, map_location=self.device, weights_only=False)
        # Extract the model from the weights
        model = weights['model']
        # Convert model to float32 precision and set to evaluation mode
        _ = model.float().eval()
        # If GPU is available, optimize model with half-precision
        if torch.cuda.is_available():
            model = model.half().to(self.device)
        print("YOLOv7 model loaded")
        return model
    
    # Convert keypoints from model space (letterboxed) back to original image space
    def unletterbox_keypoints(self, kpts, orig_shape, model_shape=(640, 640)):
        h0, w0 = orig_shape[:2]  # Original height and width
        h, w = model_shape       # Model input size (640x640)
        # Calculate gain (scaling factor) from letterbox operation
        gain = min(w / w0, h / h0)
        # Calculate padding added during letterbox
        pad_w = (w - w0 * gain) / 2
        pad_h = (h - h0 * gain) / 2
        # Debug info
        #print(f"[DEBUG] Letterbox gain: {gain}, pad_w: {pad_w}, pad_h: {pad_h}, orig_shape: {orig_shape}, model_shape: {model_shape}")
        # Make a copy of keypoints
        kpts_out = kpts.copy()
        # Reverse letterbox transformation for each keypoint
        for j in range(kpts.shape[0]):
            if kpts[j, 2] > 0.5:  # Only process high-confidence keypoints
                # Remove padding and scale back to original dimensions
                kpts_out[j, 0] = (kpts[j, 0] - pad_w) / gain
                kpts_out[j, 1] = (kpts[j, 1] - pad_h) / gain
        return kpts_out

    # Main inference function that handles proper keypoint mapping
    def inference_and_draw_on_display(self, orig_img, padded_img, scale, pad_x, pad_y, new_width, new_height):
        # Debug info about display parameters
        #print(f"[DEBUG] Display scale: {scale}, pad_x: {pad_x}, pad_y: {pad_y}, new_width: {new_width}, new_height: {new_height}")
        #print(f"[DEBUG] Original image shape: {orig_img.shape}, Padded image shape: {padded_img.shape}")
        
        # Get pose detection from the model
        img, output = self.get_pose(orig_img)
        img_pre = self.prepare_image(img)
        is_fall, bbox = self.fall_detection(output)
        img_result = padded_img.copy()

        # Draw bounding box in different color depending on is_fall
        if bbox:  # If there is a bbox, draw it
            bbox_raw = self.scale_coords(img_pre.shape, np.array([bbox]), orig_img.shape).round()
            bbox_raw[:, [0, 2]] = bbox_raw[:, [0, 2]] * scale + pad_x
            bbox_raw[:, [1, 3]] = bbox_raw[:, [1, 3]] * scale + pad_y
            print(f"[DEBUG] is_fall: {is_fall}")
            if is_fall:
                color = (0, 0, 255)  # Red
            else:
                color = (0, 255, 0)  # Green
            img_result = self.draw_bbox(img_result, bbox_raw, color=color)

        # Draw keypoints if enabled
        if self.show_keypoints and len(output) > 0:
            for i, pose in enumerate(output):
                # Extract keypoints from model output
                kpts = pose[7:].reshape(-1, 3)
                
                # Debug info for first keypoint
                #print(f"[DEBUG] First keypoint from model: {kpts[0] if kpts.shape[0] > 0 else 'N/A'}")
                
                # Convert keypoints from model space to original image space
                kpts_orig = self.unletterbox_keypoints(kpts, orig_img.shape)
                #print(f"[DEBUG] First keypoint after unletterbox: {kpts_orig[0] if kpts_orig.shape[0] > 0 else 'N/A'}")
                
                # Create a copy for visualization
                kpts_display = kpts_orig.copy()
                
                # Map each keypoint to display coordinates
                for j in range(kpts_orig.shape[0]):
                    if kpts_orig[j, 2] > 0.5:  # Only process high-confidence keypoints
                        # X-coordinate: Standard scaling
                        x = int(kpts_orig[j, 0] * scale + pad_x)
                        
                        # Y-coordinate: Apply standard scaling plus y-offset correction
                        # Calculate the offset as a percentage of the image height
                        y_offset = int(new_height * self.y_offset_factor)
                        y = int(kpts_orig[j, 1] * scale + pad_y + y_offset)
                        
                        # Update keypoints for skeleton drawing
                        kpts_display[j, 0] = x
                        kpts_display[j, 1] = y
                
                # Draw the skeleton using the transformed keypoints
                plot_skeleton_kpts(img_result, kpts_display.flatten(), 3)
                
                # Debug info for y-offset
                #print(f"[DEBUG] Current y_offset_factor: {self.y_offset_factor}, y_offset: {y_offset}")
        
        return img_result, is_fall
    
    # Toggle keypoint display on/off
    def toggle_keypoints(self):
        self.show_keypoints = not self.show_keypoints
        return self.show_keypoints
    
    # Draw red bounding box for fall detection
    def draw_bbox(self, image, bboxes, color=(0, 0, 255)):
        for box in bboxes:
            cv2.rectangle(image, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color=color,
                        thickness=2, lineType=cv2.LINE_AA)
        return image
    
    # Process image through the YOLOv7 model to get pose detection
    def get_pose(self, image):
        # Resize image to 640x640 while maintaining aspect ratio (letterbox)
        image = letterbox(image, 640, stride=64, auto=True)[0]
        # Convert to PyTorch tensor
        image = transforms.ToTensor()(image)
        # Convert to batch format (add dimension)
        image = torch.tensor(np.array([image.numpy()]))
        # Use half precision if GPU available
        if torch.cuda.is_available():
            image = image.half().to(self.device)
        # Run inference without gradient calculation
        with torch.no_grad():
            # Forward pass through the model
            output, _ = self.model(image)

        # Filter out low confidence detections using non-max suppression
        output = non_max_suppression_kpt(output, 0.25, 0.65, nc=self.model.yaml['nc'], nkpt=self.model.yaml['nkpt'],
                                        kpt_label=True)
        # Process output to extract keypoints
        with torch.no_grad():
            output = output_to_keypoint(output)

        return image, output
    
    # Convert PyTorch tensor to OpenCV image format
    def prepare_image(self, image):
        # Rearrange dimensions and scale to 0-255
        _img = image[0].permute(1, 2, 0) * 255
        # Convert to NumPy array
        _img = _img.cpu().numpy().astype(np.uint8)
        # Convert color space from BGR to RGB
        _img = cv2.cvtColor(_img, cv2.COLOR_BGR2RGB)
        # Convert back to BGR (OpenCV default)
        img = cv2.cvtColor(_img, cv2.COLOR_RGB2BGR)
        return img
    
    # Scale coordinates from model space to original image space
    def scale_coords(self, img1_shape, coords, img0_shape, ratio_pad=None):
        if ratio_pad is None:  # Calculate from img0_shape
            # Calculate gain (scaling factor)
            gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])
            # Calculate padding
            pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (img1_shape[0] - img0_shape[0] * gain) / 2
        else:
            gain = ratio_pad[0][0]
            pad = ratio_pad[1]
        # Remove padding
        coords[:, [0, 2]] -= pad[0]  # x padding
        coords[:, [1, 3]] -= pad[1]  # y padding
        # Scale coordinates
        coords[:, :4] /= gain
        # Ensure coordinates are within image boundaries
        self.clip_coords(coords, img0_shape)
        return coords

    # Ensure coordinates are within image boundaries
    def clip_coords(self, boxes, shape):
        if isinstance(boxes, torch.Tensor):  # For PyTorch tensors
            boxes[:, 0].clamp_(0, shape[1])  # x1
            boxes[:, 1].clamp_(0, shape[0])  # y1
            boxes[:, 2].clamp_(0, shape[1])  # x2
            boxes[:, 3].clamp_(0, shape[0])  # y2
        else:  # For NumPy arrays
            boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, shape[1])  # x1, x2
            boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, shape[0])  # y1, y2

    # Algorithm to detect if a person is falling
    def fall_detection(self, poses):
        for pose in poses:
            # Calculate bounding box coordinates
            xmin, ymin = (pose[2] - pose[4] / 2), (pose[3] - pose[5] / 2)
            xmax, ymax = (pose[2] + pose[4] / 2), (pose[3] + pose[5] / 2)
            
            # Extract keypoint coordinates
            left_shoulder_y = pose[23]
            left_shoulder_x = pose[22]
            right_shoulder_y = pose[26]
            left_body_y = pose[41]
            left_body_x = pose[40]
            right_body_y = pose[44]
            
            # Calculate length factor (distance between shoulder and body)
            len_factor = math.sqrt(((left_shoulder_y - left_body_y) ** 2 + (left_shoulder_x - left_body_x) ** 2))
            
            # Extract foot positions
            left_foot_y = pose[53]
            right_foot_y = pose[56]
            
            # Calculate bounding box dimensions
            dx = int(xmax) - int(xmin)
            dy = int(ymax) - int(ymin)
            difference = dy - dx
            
            # Fall detection logic based on body keypoint relationships
            # Checks if shoulders are too close to feet, or if width > height
            if left_shoulder_y > left_foot_y - len_factor and left_body_y > left_foot_y - (
                    len_factor / 2) and left_shoulder_y > left_body_y - (len_factor / 2) or (
                    right_shoulder_y > right_foot_y - len_factor and right_body_y > right_foot_y - (
                    len_factor / 2) and right_shoulder_y > right_body_y - (len_factor / 2)) \
                    or difference < 0:
                return True, [xmin, ymin, xmax, ymax]
        return False, [xmin, ymin, xmax, ymax]

    # Method to adjust the y-offset factor
    def set_y_offset_factor(self, factor):
        """Set the y-offset factor for keypoint positioning (0.0 to 1.0)"""
        self.y_offset_factor = max(0.0, min(1.0, factor))  # Clamp between 0 and 1
        return self.y_offset_factor