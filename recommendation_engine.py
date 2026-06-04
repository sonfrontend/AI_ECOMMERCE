import pandas as pd
import numpy as np
import pyodbc
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import threading

class RecommendationEngine:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.user_item_matrix = None
        self.user_similarity = None
        self.users_map = []
        self.items_map = []
        self.lock = threading.Lock()

    def fetch_data(self):
        """Fetch scoring data from SQL Server"""
        conn = pyodbc.connect(self.connection_string)
        
        # 1. Transactions/OrderDetails (10 points)
        # Assuming OrderItems table has OrderId, ProductId. We need UserId from Orders.
        # But this might be complex if table names differ. We will use generic queries.
        query_orders = """
            SELECT o.UserId, oi.ProductId, 10 as Score
            FROM Orders o
            JOIN OrderItems oi ON o.Id = oi.OrderId
            WHERE o.UserId IS NOT NULL
        """
        df_orders = pd.read_sql(query_orders, conn)

        # 2. CartItems (5 points)
        query_cart = """
            SELECT UserId, ProductId, 5 as Score
            FROM CartItems
            WHERE UserId IS NOT NULL
        """
        df_cart = pd.read_sql(query_cart, conn)

        # 3. Favorites (3 points)
        query_favorites = """
            SELECT UserId, ProductId, 3 as Score
            FROM Favorites
            WHERE UserId IS NOT NULL
        """
        df_favorites = pd.read_sql(query_favorites, conn)

        # 4. UserInteractions (1 point for view > 5s)
        # InteractionType = 1 for View > 5s
        query_interactions = """
            SELECT UserId, ProductId, Score
            FROM UserInteractions
            WHERE InteractionType = 1 AND UserId IS NOT NULL
        """
        df_interactions = pd.read_sql(query_interactions, conn)

        conn.close()

        # Combine all dataframes
        df_all = pd.concat([df_orders, df_cart, df_favorites, df_interactions])
        
        # Group by UserId and ProductId, sum the scores
        df_grouped = df_all.groupby(['UserId', 'ProductId'])['Score'].sum().reset_index()
        return df_grouped

    def train_model(self):
        """Build User-Item matrix and compute similarity"""
        with self.lock:
            try:
                df = self.fetch_data()
                if df.empty:
                    print("No data available for recommendation.")
                    return

                # Create user-item matrix
                matrix = df.pivot(index='UserId', columns='ProductId', values='Score').fillna(0)
                
                self.users_map = matrix.index.tolist()
                self.items_map = matrix.columns.tolist()
                self.user_item_matrix = matrix.values

                # Compute cosine similarity between users
                # user_similarity[i, j] is the similarity between user i and user j
                self.user_similarity = cosine_similarity(self.user_item_matrix)
                print(f"Model trained with {len(self.users_map)} users and {len(self.items_map)} products.")
            except Exception as e:
                print(f"Error training model: {e}")

    def recommend_for_user(self, user_id_str, top_k=10):
        """Recommend items for a specific user"""
        with self.lock:
            if self.user_similarity is None or self.user_item_matrix is None:
                return []
            
            # Since user_id from C# is string (GUID), we find its index
            try:
                user_idx = self.users_map.index(user_id_str)
            except ValueError:
                # User not found in history, return popular items as fallback
                return self.get_popular_items(top_k)

            # Get user similarity scores
            sim_scores = self.user_similarity[user_idx]
            
            # Predict scores for all items
            # Weighted average of item scores from other users
            item_scores = np.zeros(len(self.items_map))
            sim_sum = np.sum(np.abs(sim_scores)) - 1 # excluding self
            
            if sim_sum == 0:
                return self.get_popular_items(top_k)
                
            for i in range(len(self.users_map)):
                if i != user_idx:
                    item_scores += sim_scores[i] * self.user_item_matrix[i]
                    
            item_scores = item_scores / sim_sum

            # Set score of already interacted items to 0 so we don't recommend them
            user_interacted = self.user_item_matrix[user_idx] > 0
            item_scores[user_interacted] = 0

            # Get top K indices
            top_indices = np.argsort(item_scores)[::-1][:top_k]
            
            recommendations = []
            for idx in top_indices:
                if item_scores[idx] > 0:
                    recommendations.append(self.items_map[idx])
            
            if not recommendations:
                return self.get_popular_items(top_k)

            return recommendations

    def recommend_fbt(self, product_id, top_k=5):
        """Recommend Frequently Bought Together items based on in-memory co-occurrence"""
        with self.lock:
            if self.user_item_matrix is None:
                return []
                
            try:
                item_idx = self.items_map.index(product_id)
            except ValueError:
                return self.get_popular_items(top_k)

            # Lấy vector người dùng đã tương tác với sản phẩm này
            item_col = self.user_item_matrix[:, item_idx]
            
            # Lấy index của những user đó
            user_indices = np.where(item_col > 0)[0]
            if len(user_indices) == 0:
                return self.get_popular_items(top_k)
                
            # Tính tổng điểm tương tác của các sản phẩm khác mà những user này đã tương tác (Co-occurrence)
            co_scores = np.sum(self.user_item_matrix[user_indices, :], axis=0)
            
            # Loại trừ chính sản phẩm đang xét
            co_scores[item_idx] = 0
            
            # Lấy top K sản phẩm có điểm đồng xuất hiện cao nhất
            top_indices = np.argsort(co_scores)[::-1][:top_k]
            
            recommendations = []
            for idx in top_indices:
                if co_scores[idx] > 0:
                    recommendations.append(self.items_map[idx])
                    
            if not recommendations:
                return self.get_popular_items(top_k)
                
            return recommendations

    def get_popular_items(self, top_k=10):
        """Fallback: Return most interacted items"""
        if self.user_item_matrix is None:
            return []
        
        item_scores = np.sum(self.user_item_matrix, axis=0)
        top_indices = np.argsort(item_scores)[::-1][:top_k]
        return [self.items_map[i] for i in top_indices if item_scores[i] > 0]
