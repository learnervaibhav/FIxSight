import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import PolynomialFeatures, StandardScaler

class RidgeRegression:
    """
    The following class is closed form solution of ridge regression.
    """

    def __init__(self, alpha=0):
        self.alpha = alpha
        self.weights = None

    def fit(self, X, y):

        n_samples, n_features = X.shape

        X = np.c_[np.ones((n_samples,1)), X]

        I = np.eye(n_features+1)
        
        I[0,0] = 0  # biase term will never change

        self.weights = np.linalg.inv(
            X.T @ X + self.alpha*I
        ) @ X.T @ y

    def predict(self,X):

        X = np.c_[np.ones((len(X),1)), X]

        return X @ self.weights


np.random.seed(42)

X = 3*np.random.rand(20,1)

y = 1 + 0.5*X[:,0] + np.random.randn(20)

# Points for plotting curve

X_plot = np.linspace(0,3,500).reshape(-1,1)



alphas_linear = [0,10,100]

plt.figure(figsize=(14,6))

plt.subplot(1,2,1)

plt.scatter(X,y,color="royalblue",s=30)

for alpha in alphas_linear:

    model = RidgeRegression(alpha)

    model.fit(X,y)

    y_pred = model.predict(X_plot)

    plt.plot(
        X_plot,
        y_pred,
        linewidth=2,
        label=fr"$\alpha={alpha}$"
    )

plt.title("Linear Ridge Regression")
plt.xlabel("$x_1$")
plt.ylabel("$y$")
plt.legend()
plt.grid(True)



plt.subplot(1,2,2)

plt.scatter(X,y,color="royalblue",s=30)

poly = PolynomialFeatures(
    degree=10,
    include_bias=False
)

X_poly = poly.fit_transform(X)

X_plot_poly = poly.transform(X_plot)

scaler = StandardScaler()

X_poly = scaler.fit_transform(X_poly)

X_plot_poly = scaler.transform(X_plot_poly)

alphas_poly = [0,1e-5,1]

for alpha in alphas_poly:

    model = RidgeRegression(alpha)

    model.fit(X_poly,y)

    y_pred = model.predict(X_plot_poly)

    plt.plot(
        X_plot,
        y_pred,
        linewidth=2,
        label=fr"$\alpha={alpha}$"
    )

plt.title("Polynomial Ridge Regression (Degree = 10)")
plt.xlabel("$x_1$")
plt.ylabel("$y$")
plt.legend()
plt.grid(True)

plt.tight_layout()

plt.show()