import torch
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np

class FeatureExtractor:
    def __init__(self):
        # Load a pre-trained ResNet50 model
        self.model = models.resnet50(pretrained=True)
        # We only want to extract features, so remove the last classification layer
        self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
        self.model.eval() # Set to evaluation mode
        
        # Define the image transformations required by ResNet50
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def extract(self, img):
        """
        Extract feature vector from a PIL image.
        Returns a 1D numpy array.
        """
        # Ensure image is in RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Preprocess the image
        img_tensor = self.transform(img)
        img_tensor = img_tensor.unsqueeze(0) # Add batch dimension (1, 3, 224, 224)
        
        # Extract features
        with torch.no_grad():
            feature = self.model(img_tensor)
            
        # Flatten the feature tensor to a 1D array
        feature = feature.squeeze().numpy()
        
        # Normalize the feature vector (L2 norm) for cosine similarity
        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm
            
        return feature
