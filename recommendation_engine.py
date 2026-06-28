import pandas as pd
import numpy as np
import pyodbc
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import threading

class RecommendationEngine:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        
        # Matrix CF
        self.cf_user_item_matrix = None
        self.cf_user_similarity = None
        self.cf_users_map = []
        self.cf_items_map = []
        
        # Matrix FBT
        self.fbt_user_item_matrix = None
        self.fbt_users_map = []
        self.fbt_items_map = []
        
        self.lock = threading.Lock()

    def fetch_fbt_data(self):
        """Fetch data only from Transactions for FBT (Sản phẩm đi kèm)"""
        conn = pyodbc.connect(self.connection_string)
        
        query_fbt = """
            SELECT CAST(oi.OrderId AS VARCHAR(50)) AS UserId, 
                   CAST(pv.ProductId AS VARCHAR(50)) AS ProductId, 
                   1 AS Score
            FROM OrderItems oi
            JOIN ProductVariants pv ON oi.VariantId = pv.VariantId
            WHERE oi.OrderId IS NOT NULL AND pv.ProductId IS NOT NULL
        """
        df_fbt = pd.read_sql(query_fbt, conn)
        conn.close()
        
        # Group to avoid duplicates, sum the score (co-occurrence weight)
        df_grouped = df_fbt.groupby(['UserId', 'ProductId'])['Score'].sum().reset_index()
        return df_grouped

    def fetch_cf_data(self):
        """Fetch data from UserInteractions for CF (Gợi ý cá nhân)"""
        conn = pyodbc.connect(self.connection_string)
        
        query_interactions = """
            SELECT CAST(UserId AS VARCHAR(50)) AS UserId, 
                   CAST(ProductId AS VARCHAR(50)) AS ProductId, 
                   Score
            FROM UserInteractions
            WHERE UserId IS NOT NULL AND ProductId IS NOT NULL
        """
        df_interactions = pd.read_sql(query_interactions, conn)
        conn.close()
        
        # Đưa ID về chữ thường để tránh lỗi 1 user bị tách làm 2 (do C# lưu lúc hoa lúc thường)
        df_interactions['UserId'] = df_interactions['UserId'].str.lower()
        
        # Lấy max score nếu có duplicate
        df_grouped = df_interactions.groupby(['UserId', 'ProductId'])['Score'].max().reset_index()
        return df_grouped

    def train_model(self):
        """Build both User-Item matrices"""
        with self.lock:
            try:
                # 1. Train FBT Matrix
                df_fbt = self.fetch_fbt_data()
                if not df_fbt.empty:
                    matrix_fbt = df_fbt.pivot(index='UserId', columns='ProductId', values='Score').fillna(0)
                    self.fbt_users_map = matrix_fbt.index.tolist()
                    self.fbt_items_map = matrix_fbt.columns.tolist()
                    self.fbt_user_item_matrix = matrix_fbt.values
                    print(f"FBT Matrix trained with {len(self.fbt_users_map)} users and {len(self.fbt_items_map)} products.")

                # 2. Train CF Matrix
                df_cf = self.fetch_cf_data()
                if not df_cf.empty:
                    matrix_cf = df_cf.pivot(index='UserId', columns='ProductId', values='Score').fillna(0)
                    self.cf_users_map = matrix_cf.index.tolist()
                    self.cf_items_map = matrix_cf.columns.tolist()
                    self.cf_user_item_matrix = matrix_cf.values
                    
                    # Compute Cosine Similarity
                    self.cf_user_similarity = cosine_similarity(self.cf_user_item_matrix)
                    print(f"CF Matrix trained with {len(self.cf_users_map)} users and {len(self.cf_items_map)} products.")
            except Exception as e:
                print(f"Error training model: {e}")

    def recommend_for_user(self, user_id_str, top_k=12):
        """Recommend items for a specific user using CF Matrix"""
        with self.lock:
            if self.cf_user_similarity is None or self.cf_user_item_matrix is None:
                return []
            
            try:
                user_idx = self.cf_users_map.index(str(user_id_str).lower())
            except ValueError:
                return self.get_popular_items(top_k, use_cf=True, user_id_str=user_id_str)

            sim_scores = self.cf_user_similarity[user_idx]
            item_scores = np.zeros(len(self.cf_items_map))
            sim_sum = np.sum(np.abs(sim_scores)) - 1
            
            if sim_sum <= 1e-9:
                return []
                
            for i in range(len(self.cf_users_map)):
                if i != user_idx:
                    item_scores += sim_scores[i] * self.cf_user_item_matrix[i]
                    
            item_scores = item_scores / sim_sum

            user_interacted = self.cf_user_item_matrix[user_idx] == 5
            item_scores[user_interacted] = 0

            top_indices = np.argsort(item_scores)[::-1][:top_k]
            
            recommendations = []
            for idx in top_indices:
                if item_scores[idx] > 0:
                    recommendations.append(self.cf_items_map[idx])
            
            if not recommendations:
                return []

            return recommendations

    def recommend_fbt(self, product_id, top_k=5):
        """Recommend Frequently Bought Together items using FBT Matrix"""
        with self.lock:
            if self.fbt_user_item_matrix is None:
                return []
                
            try:
                item_idx = self.fbt_items_map.index(str(product_id))
            except ValueError:
                return []

            item_col = self.fbt_user_item_matrix[:, item_idx]
            user_indices = np.where(item_col > 0)[0]
            
            if len(user_indices) == 0:
                return []
                
            co_scores = np.sum(self.fbt_user_item_matrix[user_indices, :], axis=0)
            co_scores[item_idx] = 0
            
            top_indices = np.argsort(co_scores)[::-1][:top_k]
            
            recommendations = []
            for idx in top_indices:
                if co_scores[idx] > 0:
                    recommendations.append(self.fbt_items_map[idx])
                    
            if not recommendations:
                return []
                
            return recommendations

    def get_popular_items(self, top_k=10, use_cf=True, exclude_user_idx=None, user_id_str=None):
        """Fallback: Return most sold and favorited items from DB"""
        try:
            conn = pyodbc.connect(self.connection_string)
            
            exclude_query = ""
            params = []
            if user_id_str:
                exclude_query = "AND p.ProductId NOT IN (SELECT ProductId FROM UserInteractions WHERE UserId = ? AND InteractionType = 'PURCHASE')"
                params.append(str(user_id_str))
                
            query = f"""
                SELECT TOP {top_k} p.ProductId 
                FROM Products p
                LEFT JOIN Favorites f ON p.ProductId = f.ProductId
                WHERE p.IsActived = 1 {exclude_query}
                GROUP BY p.ProductId, p.SoldQuantity
                ORDER BY p.SoldQuantity DESC, COUNT(f.Id) DESC
            """
            
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            
            if not df.empty:
                return df['ProductId'].astype(str).tolist()
        except Exception as e:
            print(f"Error fetching popular items from DB: {e}")

        # Fallback if DB query fails
        matrix = self.cf_user_item_matrix if use_cf else self.fbt_user_item_matrix
        items_map = self.cf_items_map if use_cf else self.fbt_items_map
        
        if matrix is None:
            return []
        
        item_scores = np.sum(matrix, axis=0)
        
        if exclude_user_idx is not None and use_cf:
            user_interacted = matrix[exclude_user_idx] == 5
            item_scores[user_interacted] = 0

        top_indices = np.argsort(item_scores)[::-1][:top_k]
        return [items_map[i] for i in top_indices if item_scores[i] > 0]
