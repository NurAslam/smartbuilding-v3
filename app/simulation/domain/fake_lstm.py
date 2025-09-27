from sklearn.neural_network import MLPRegressor

class FakeLSTMRegressor:
    def __init__(self, n_features: int, random_state: int = 42):
        self.n_features = n_features
        self.model = MLPRegressor(
            hidden_layer_sizes=(16,),
            activation="relu",
            solver="adam",
            max_iter=400,
            random_state=random_state,
        )
    def fit(self, X, y, epochs: int = 1, batch_size: int = 32, verbose: int = 0):
        X2 = X.reshape((X.shape[0], self.n_features))
        self.model.fit(X2, y)
        return self
    def predict(self, X, verbose: int = 0):
        X2 = X.reshape((X.shape[0], self.n_features))
        return self.model.predict(X2)

def make_lstm(n_features: int):
    return FakeLSTMRegressor(n_features=n_features, random_state=42)
