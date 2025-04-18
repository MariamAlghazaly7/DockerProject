from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import numpy as np
import shutil
import os
from VGG_feature_extractor import VGGNet
from scipy.spatial import distance
from pathlib import Path
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/images", StaticFiles(directory="temp"), name="images")

# Initialize your model
model = VGGNet()

# Load existing data with validation
def load_data():
    try:
        structured_data = np.load("FoundFeaturesWithNames.npy", allow_pickle=True)
        structured_data2 = np.load("UnfoundFeaturesWithNames.npy", allow_pickle=True)
        print(structured_data2['features'])
        print(structured_data2['image_name'])
        feats = structured_data['features']
        imgNames = structured_data['image_name']
        
        # Check if the features and image names arrays are empty
        if structured_data2.size == 0:
            feats2 = np.empty((0, feats.shape[1]))  # Create an empty array with the same feature dimensions
            imgNames2 = np.array([], dtype="<U50")
        else:
            feats2 = structured_data2['features']
            imgNames2 = structured_data2['image_name']
        
        return feats, imgNames, feats2, imgNames2

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

# Load data initially
feats, imgNames, feats2, imgNames2 = load_data()

class QueryResponse(BaseModel):
    message: str
    images: list[str] = []
    status: str

# Helper function to check the image format
def is_valid_image(file_name: str) -> bool:
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    return Path(file_name).suffix.lower() in allowed_extensions
@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)) -> QueryResponse:
    global feats2, imgNames2  # Declare global variables

    # Validate the image format
    if not is_valid_image(file.filename):
        raise HTTPException(status_code=400, detail="Invalid image format. Only .jpg, .jpeg, and .png are allowed.")
    
    # Save the uploaded image
    img_path = f"temp/{file.filename}"
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    with open(img_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process the uploaded image
    try:
        query_img = img_path
        print("Searching for similar images")

        # Feature extraction
        X = model.extract_feat(query_img)
        print("Extracted feature for query image:", X)

        # Compare with existing features
        scores = []
        for i in range(feats2.shape[0]):
            score = 1 - distance.cosine(X, feats2[i])
            scores.append(score)

        print("Scores after comparing features:", scores)

        scores = np.array(scores)
        rank_ID = np.argsort(scores)[::-1]
        rank_score = scores[rank_ID]

        print("Ranked IDs:", rank_ID)
        print("Top Scores:", rank_score)

        maxres = 3
        base_url = "http://localhost:8000/images/"
        imlist = [f"{base_url}{imgNames2[i]}" for i in rank_ID[:maxres]]
        # imlist = [imgNames2[i] for i in rank_ID[:maxres]]

        threshold = 0.5  # Lower threshold for testing
        response = {
            "message": "Searching completed.",
            "status": "success",
        }

        if all(score < threshold for score in rank_score):
            # No match, adding image to the database
            img_name = query_img.split('/')[-1]
            feats2 = np.append(feats2, [X], axis=0)
            imgNames2 = np.append(imgNames2, [img_name])

            # Save the updated data back to the file
            new_structured_data2 = np.empty(feats2.shape[0], dtype=[('features', 'float32', (feats2.shape[1],)), ('image_name', 'U50')])
            new_structured_data2['features'] = feats2
            new_structured_data2['image_name'] = imgNames2
            np.save("UnfoundFeaturesWithNames.npy", new_structured_data2)

            response["message"] = "No matches found, added to the database."
            response["status"] = "added"
        else:
            # Save the updated data back to the file
          
            # Return top results
            response["images"] = imlist
            response["message"] = "Top images found in the database."
            response["status"] = "found"

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Start the API with Uvicorn (Run the following in terminal)
# uvicorn app:app --reload

@app.delete("/clear-images/")
async def clear_images():
    global feats2, imgNames2  # Access the global variables

    # Reset the feature and image name arrays
    feats2 = np.empty((0, feats2.shape[1]))  # Empty array with correct feature dimensions
    imgNames2 = np.array([], dtype="<U50")

    # Save the empty data back to the file
    new_structured_data2 = np.empty(0, dtype=[('features', 'float32', (feats2.shape[1],)), ('image_name', 'U50')])
    np.save("UnfoundFeaturesWithNames.npy", new_structured_data2)

    # Optionally delete all files in the temp folder
    temp_folder = "temp"
    for filename in os.listdir(temp_folder):
        file_path = os.path.join(temp_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting file {filename}: {str(e)}")

    return {"message": "All images have been cleared from the model and storage.", "status": "success"}