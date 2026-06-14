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
            SELECT CAST(t.CustomerId AS VARCHAR(50)) AS UserId, 
                   CAST(pv.ProductId AS VARCHAR(50)) AS ProductId, 
                   1 AS Score
            FROM Transactions t
            JOIN ProductVariants pv ON t.VariantId = pv.VariantId
            WHERE t.CustomerId IS NOT NULL AND pv.ProductId IS NOT NULL
        """
        df_fbt = pd.read_sql(query_fbt, conn)
        conn.close()
        
        # Group to avoid duplicates, sum the score (co-occurrence weight)
        df_grouped = df_fbt.groupby(['UserId', 'ProductId'])['Score'].sum().reset_index()
        return df_grouped

    def fetch_cf_data(self):
        """Fetch data from Transactions + UserInteractions for CF (Gợi ý cá nhân)"""
        conn = pyodbc.connect(self.connection_string)
        
        query_transactions = """
            SELECT CAST(t.CustomerId AS VARCHAR(50)) AS UserId, 
                   CAST(pv.ProductId AS VARCHAR(50)) AS ProductId, 
                   5 AS Score
            FROM Transactions t
            JOIN ProductVariants pv ON t.VariantId = pv.VariantId
            WHERE t.CustomerId IS NOT NULL AND pv.ProductId IS NOT NULL
        """
        df_trans = pd.read_sql(query_transactions, conn)
        
        query_interactions = """
            SELECT CAST(UserId AS VARCHAR(50)) AS UserId, 
                   CAST(ProductId AS VARCHAR(50)) AS ProductId, 
                   Score
            FROM UserInteractions
            WHERE UserId IS NOT NULL AND ProductId IS NOT NULL
        """
        df_interactions = pd.read_sql(query_interactions, conn)
        conn.close()
        
        df_all = pd.concat([df_trans, df_interactions])
        
        # Lấy max score nếu có duplicate
        df_grouped = df_all.groupby(['UserId', 'ProductId'])['Score'].max().reset_index()
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

    def recommend_for_user(self, user_id_str, top_k=10):
        """Recommend items for a specific user using CF Matrix"""
        with self.lock:
            if self.cf_user_similarity is None or self.cf_user_item_matrix is None:
                return []
            
            try:
                user_idx = self.cf_users_map.index(str(user_id_str))
            except ValueError:
                return self.get_popular_items(top_k, use_cf=True)

            sim_scores = self.cf_user_similarity[user_idx]
            item_scores = np.zeros(len(self.cf_items_map))
            sim_sum = np.sum(np.abs(sim_scores)) - 1
            
            if sim_sum == 0:
                return self.get_popular_items(top_k, use_cf=True)
                
            for i in range(len(self.cf_users_map)):
                if i != user_idx:
                    item_scores += sim_scores[i] * self.cf_user_item_matrix[i]
                    
            item_scores = item_scores / sim_sum

            user_interacted = self.cf_user_item_matrix[user_idx] > 0
            item_scores[user_interacted] = 0

            top_indices = np.argsort(item_scores)[::-1][:top_k]
            
            recommendations = []
            for idx in top_indices:
                if item_scores[idx] > 0:
                    recommendations.append(self.cf_items_map[idx])
            
            if not recommendations:
                return self.get_popular_items(top_k, use_cf=True)

            return recommendations

    def recommend_fbt(self, product_id, top_k=5):
        """Recommend Frequently Bought Together items using FBT Matrix"""
        with self.lock:
            if self.fbt_user_item_matrix is None:
                return self.get_popular_items(top_k, use_cf=False)
                
            try:
                item_idx = self.fbt_items_map.index(str(product_id))
            except ValueError:
                return self.get_popular_items(top_k, use_cf=False)

            item_col = self.fbt_user_item_matrix[:, item_idx]
            user_indices = np.where(item_col > 0)[0]
            
            if len(user_indices) == 0:
                return self.get_popular_items(top_k, use_cf=False)
                
            co_scores = np.sum(self.fbt_user_item_matrix[user_indices, :], axis=0)
            co_scores[item_idx] = 0
            
            top_indices = np.argsort(co_scores)[::-1][:top_k]
            
            recommendations = []
            for idx in top_indices:
                if co_scores[idx] > 0:
                    recommendations.append(self.fbt_items_map[idx])
                    
            if not recommendations:
                return self.get_popular_items(top_k, use_cf=False)
                
            return recommendations

    def get_popular_items(self, top_k=10, use_cf=True):
        """Fallback: Return most interacted items"""
        matrix = self.cf_user_item_matrix if use_cf else self.fbt_user_item_matrix
        items_map = self.cf_items_map if use_cf else self.fbt_items_map
        
        if matrix is None:
            return []
        
        item_scores = np.sum(matrix, axis=0)
        top_indices = np.argsort(item_scores)[::-1][:top_k]
        return [items_map[i] for i in top_indices if item_scores[i] > 0]
