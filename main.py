from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pickle
import numpy as np
from PIL import Image
import io
import os
from feature_extractor import FeatureExtractor

app = FastAPI(title="AI Image Search API")

# Setup CORS (just in case)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
fe = None
features_dict = None
article_ids = None
feature_matrix = None

class RecommendRequest(BaseModel):
    article_ids: List[str]
    top_k: int = 15

@app.on_event("startup")
async def startup_event():
    global fe, features_dict, article_ids, feature_matrix
    print("Loading Feature Extractor Model...")
    fe = FeatureExtractor()
    
    print("Loading Indexed Features...")
    if os.path.exists('image_features.pkl'):
        with open('image_features.pkl', 'rb') as f:
            features_dict = pickle.load(f)
            
        article_ids = list(features_dict.keys())
        # feature_matrix shape: (num_images, 2048)
        feature_matrix = np.array([features_dict[aid] for aid in article_ids])
        print(f"Loaded {len(article_ids)} features.")
    else:
        print("Warning: image_features.pkl not found. Please run index_images.py first.")
        features_dict = {}
        article_ids = []
        feature_matrix = np.array([])

@app.post("/api/predict", response_model=List[str])
async def predict(image: UploadFile = File(...), top_k: int = 12):
    global fe, article_ids, feature_matrix
    
    if feature_matrix.shape[0] == 0:
        raise HTTPException(status_code=500, detail="Feature DB is empty. Run index_images.py")
        
    try:
        # Read image
        contents = await image.read()
        img = Image.open(io.BytesIO(contents))
        
        # Extract feature
        query_feature = fe.extract(img)
        
        # Calculate Cosine Similarity
        # Since vectors are L2 normalized, dot product is cosine similarity
        similarities = np.dot(feature_matrix, query_feature)
        
        # Get top K indices
        # argsort sorts ascending, so we take the last K and reverse
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Get corresponding article IDs
        top_article_ids = [article_ids[i] for i in top_indices]
        
        return top_article_ids
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recommend-by-history", response_model=List[str])
async def recommend_by_history(req: RecommendRequest):
    global features_dict, article_ids, feature_matrix
    
    if feature_matrix.shape[0] == 0:
        raise HTTPException(status_code=500, detail="Feature DB is empty. Run index_images.py")
        
    try:
        valid_features = []
        for aid in req.article_ids:
            if aid in features_dict:
                valid_features.append(features_dict[aid])
                
        if not valid_features:
            raise HTTPException(status_code=400, detail="None of the provided article_ids exist in the DB.")
            
        # 1. Tính trung bình cộng của các vector (Mean Vector)
        mean_vector = np.mean(valid_features, axis=0)
        
        # 2. Chuẩn hóa L2 (L2 Normalization)
        mean_vector = mean_vector / np.linalg.norm(mean_vector)
        
        # 3. Tính độ tương đồng
        similarities = np.dot(feature_matrix, mean_vector)
        
        # 4. Lấy top K + n (để trừ hao những sản phẩm đã xem)
        k_to_fetch = req.top_k + len(req.article_ids)
        top_indices = np.argsort(similarities)[-k_to_fetch:][::-1]
        
        history_set = set(req.article_ids)
        recommended_ids = []
        
        for idx in top_indices:
            aid = article_ids[idx]
            # Bỏ qua những sản phẩm đã có trong lịch sử
            if aid not in history_set:
                recommended_ids.append(aid)
            if len(recommended_ids) == req.top_k:
                break
                
        return recommended_ids
        
    except Exception as e:
        print(f"Error during recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
