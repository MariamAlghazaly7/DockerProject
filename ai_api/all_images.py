import os
import numpy as np
from VGG_feature_extractor import VGGNet

images_path = "found"
img_list = [os.path.join(images_path, f) for f in os.listdir(images_path)]

print("Start feature extraction")

model = VGGNet()

path = "found/"

feats = []
names = []

for im in os.listdir(path): 
    print("Extracting features from image - ", im)
    X = model.extract_feat(os.path.join(path, im))

    feats.append(X)
    names.append(im)

feats = np.array(feats)

dtype = [('features', 'float32', (feats.shape[1],)), ('image_name', 'U50')]
structured_data = np.empty(feats.shape[0], dtype=dtype)

structured_data['features'] = feats
structured_data['image_name'] = names

output_npy = "FoundFeaturesWithNames.npy"
np.save(output_npy, structured_data)

print(f"Features and names saved successfully to {output_npy}!")