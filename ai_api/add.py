from VGG_feature_extractor import VGGNet
import numpy as np
import cv2
import shutil  
import os
from scipy import spatial

structured_data2 = np.load("UnfoundFeaturesWithNames.npy", allow_pickle=True)
structured_data = np.load("FoundFeaturesWithNames.npy", allow_pickle=True)

feats = structured_data['features']
imgNames = structured_data['image_name']

feats2 = structured_data2['features']
imgNames2 = structured_data2['image_name']
print(imgNames2)

newImg = "test_images/apple.png"

model = VGGNet()

X = model.extract_feat(newImg)

scores = []
for i in range(feats2.shape[0]):
    score = 1 - spatial.distance.cosine(X, feats2[i])
    scores.append(score)

scores = np.array(scores)   
rank_ID = np.argsort(scores)[::-1]  
rank_score = scores[rank_ID] 

maxres = 3
imlist = [imgNames2[index] for i, index in enumerate(rank_ID[0:maxres])]

threshold = 0.8

if all(score < threshold for score in rank_score):
    print("Nobody is looking for this, we will add this to the list of things found.")
    
    feats = np.append(feats, [X], axis=0)  
    img_name = newImg.split('/')[-1]  
    imgNames = np.append(imgNames, [img_name]) 

    new_structured_data = np.empty(feats.shape[0], dtype=[('features', 'float32', (feats.shape[1],)), ('image_name', 'U50')])
    new_structured_data['features'] = feats
    new_structured_data['image_name'] = imgNames

    np.save("FoundFeaturesWithNames.npy", new_structured_data)

    destination_path = f"found/{img_name}"
    shutil.copy(newImg, destination_path)  

    print("Added the query image features and name to the database.")
    print(f"Image copied to {destination_path}.")
    
else:
    print("Top %d images in order are: " % maxres, imlist)

    first_image_path = f"unfound_yet/{imlist[0]}"
    print("Path of the first image match:", first_image_path)
    img = cv2.imread(first_image_path)
    cv2.imshow('Image', img)
    cv2.waitKey(2500)
    cv2.destroyAllWindows()
    print("Someone is already looking for this, we will send them your information.")

    first_match_name = imlist[0]
    first_match_index = np.where(imgNames2 == first_match_name)[0][0]

    feats2 = np.delete(feats2, first_match_index, axis=0)
    imgNames2 = np.delete(imgNames2, first_match_index)

    if os.path.exists(first_image_path):
        os.remove(first_image_path)
        print(f"Removed image {first_match_name} from unfound folder.")

    new_structured_data = np.empty(feats2.shape[0], dtype=[('features', 'float32', (feats2.shape[1],)), ('image_name', 'U50')])
    new_structured_data['features'] = feats2
    new_structured_data['image_name'] = imgNames2

    np.save("UnfoundFeaturesWithNames.npy", new_structured_data)
    print("Updated the database after deletion.")
    print(imgNames2)
