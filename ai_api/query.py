from VGG_feature_extractor import VGGNet
import numpy as np
import cv2
import shutil  
import os
from scipy import spatial

structured_data = np.load("FoundFeaturesWithNames.npy", allow_pickle=True)
structured_data2 = np.load("UnfoundFeaturesWithNames.npy", allow_pickle=True)

feats = structured_data['features']
imgNames = structured_data['image_name']

feats2 = structured_data2['features']
imgNames2 = structured_data2['image_name']

queryImg = "test_images/apple.png"

print("Searching for similar images")

model = VGGNet()

X = model.extract_feat(queryImg)

scores = []
for i in range(feats.shape[0]):
    score = 1 - spatial.distance.cosine(X, feats[i])
    scores.append(score)

scores = np.array(scores)   
rank_ID = np.argsort(scores)[::-1]  
rank_score = scores[rank_ID] 

maxres = 3
imlist = [imgNames[index] for i, index in enumerate(rank_ID[0:maxres])]

threshold = 0.7 

if all(score < threshold for score in rank_score):
    print("No matching images found in the database.")
    
    feats2 = np.append(feats2, [X], axis=0)  
    img_name = queryImg.split('/')[-1]  
    imgNames2 = np.append(imgNames2, [img_name]) 

    new_structured_data2 = np.empty(feats2.shape[0], dtype=[('features', 'float32', (feats2.shape[1],)), ('image_name', 'U50')])
    new_structured_data2['features'] = feats2
    new_structured_data2['image_name'] = imgNames2

    np.save("UnfoundFeaturesWithNames.npy", new_structured_data2)

    destination_path = f"unfound_yet/{img_name}"
    shutil.copy(queryImg, destination_path)  

    print("Added the query image features and name to the database.")
    print(f"Image copied to {destination_path}.")
    
else:
    print("Top %d images in order are: " % maxres, imlist)

    first_image_path = f"found/{imlist[0]}"
    print("Path of the first image match:", first_image_path)
    img = cv2.imread(first_image_path)
    cv2.imshow('Image', img)
    cv2.waitKey(2500)
    flag = input("Is this what you're missing? y/n ")
    cv2.destroyAllWindows()

    if(flag== "y"):
        first_match_name = imlist[0]
        first_match_index = np.where(imgNames == first_match_name)[0][0]

        feats = np.delete(feats, first_match_index, axis=0)
        imgNames = np.delete(imgNames, first_match_index)

        if os.path.exists(first_image_path):
            os.remove(first_image_path)
            print(f"Removed image {first_match_name} from found folder.")

        new_structured_data = np.empty(feats.shape[0], dtype=[('features', 'float32', (feats.shape[1],)), ('image_name', 'U50')])
        new_structured_data['features'] = feats
        new_structured_data['image_name'] = imgNames

        np.save("FoundFeaturesWithNames.npy", new_structured_data)
        print("Updated the database after deletion.")

    else:
        print("Sorry about that, try searching later.")

        feats2 = np.append(feats2, [X], axis=0)  
        img_name = queryImg.split('/')[-1]  
        imgNames2 = np.append(imgNames2, [img_name]) 

        new_structured_data2 = np.empty(feats2.shape[0], dtype=[('features', 'float32', (feats2.shape[1],)), ('image_name', 'U50')])
        new_structured_data2['features'] = feats2
        new_structured_data2['image_name'] = imgNames2

        np.save("UnfoundFeaturesWithNames.npy", new_structured_data2)

        destination_path = f"unfound_yet/{img_name}"
        shutil.copy(queryImg, destination_path)  

        print("Added the query image features and name to the database.")
        print(f"Image copied to {destination_path}.")    