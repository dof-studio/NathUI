# multi_universal_sampler.py

# des
#
# Multivariate distribution sampling library, supports three modes:

# Continuous distributions (multivariate): pass the target density function target(x), where x is a multivariate vector.
# Discrete distributions (multivariate): pass a dictionary or a list of tuples [(value, weight), ...], where value is a multivariate value (e.g., a tuple).
# Continuous distributions discretized into discrete points (multivariate): pass a pair (points, densities), where points is an array of support points with shape (n, d) and densities are the corresponding unnormalized densities.
# This library allows you to sample from various types of multivariate distributions, whether they are continuous, discrete, or discretized versions of continuous distributions.

import numpy as np
from typing import Callable, List, Union, Dict, Any
import logging

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MDSampler:
    """
    Multivariate Distribution Sampler:
    
    Supports three modes:
        - Continuous: Continuous distribution, where `target` is a callable function, and the input is a multivariate vector.
        - Discrete: Discrete distribution, where `target` is a dictionary or a list of tuples `[(value, weight), ...]`, and `value` represents multivariate values (e.g., a tuple).
        - Discretized: Continuous distributions discretized into discrete points, where `target` is a pair `(points, densities)`. Here, `points` is an array with shape `(n, d)` representing the support points, and `densities` is a sequence of unnormalized densities with length `n`.
    """

    def __init__(self, target: Union[
            Callable[[np.ndarray], float],
            Dict[Any, float],
            List[Any],
            tuple
        ]):
        self.target = target
        if callable(target):
            self.mode = "continuous"
            logger.info("Initialized in continuous mode (multi-dimensional).")
        elif isinstance(target, dict):
            self.mode = "discrete"
            self._prepare_discrete_from_dict()
            logger.info("Initialized in discrete mode (multi-dimensional) from dict.")
        elif isinstance(target, tuple):
            # Regard as (points, densities)
            if len(target) == 2:
                self.mode = "discretized"
                self._prepare_discretized()
                logger.info("Initialized in discretized mode (multi-dimensional) from tuple.")
            else:
                raise ValueError("Tuple input must have length 2: (points, densities).")
        elif isinstance(target, list):
            # Judgment list format:
            # If the length is 2 and the element is not a (value, weight) pair, it is considered as (points, densities)
            if len(target) == 2 and not all(isinstance(item, (list, tuple)) and len(item) == 2 for item in target):
                self.mode = "discretized"
                self._prepare_discretized()
                logger.info("Initialized in discretized mode (multi-dimensional) from list of two elements.")
            elif all(isinstance(item, (list, tuple)) and len(item) == 2 for item in target):
                self.mode = "discrete"
                self.target = dict(target)
                self._prepare_discrete_from_dict()
                logger.info("Initialized in discrete mode (multi-dimensional) from list of pairs.")
            else:
                raise ValueError("List input format not recognized.")
        else:
            raise ValueError("Unsupported target type. Must be callable, dict, list or tuple.")

    def _prepare_discrete_from_dict(self):
        """
        Preprocess the discrete distribution (in dictionary form):
                - Convert keys to tuples (to ensure multi-dimensionality);
                - Normalize the weights and construct the cumulative distribution for sampling.
        """
        keys = list(self.target.keys())
        # Make sure each key is a tuple (if it is a list or np.ndarray, convert it to a tuple)
        self.discrete_values = [tuple(k) if isinstance(k, (list, np.ndarray)) else k for k in keys]
        probs = np.array([self.target[k] for k in keys], dtype=float)
        total = probs.sum()
        if total <= 0:
            raise ValueError("Sum of probabilities must be positive.")
        self.discrete_probs = probs / total
        self.cumulative_probs = np.cumsum(self.discrete_probs)
        logger.debug(f"Discrete cumulative probabilities: {self.cumulative_probs}")

    def _prepare_discretized(self):
        """
        Preprocess the discretized continuous distribution:
                - target should be in the form of (points, densities);
                - Normalize the density and construct the cumulative distribution for sampling.
        """
        points = np.asarray(self.target[0])
        densities = np.asarray(self.target[1], dtype=float)
        if points.shape[0] != densities.shape[0]:
            raise ValueError("Points and densities must have the same length.")
        total = densities.sum()
        if total <= 0:
            raise ValueError("Sum of densities must be positive.")
        self.discrete_values = points  # points 的 shape 为 (n, d)
        self.discrete_probs = densities / total
        self.cumulative_probs = np.cumsum(self.discrete_probs)
        logger.debug(f"Discretized cumulative probabilities: {self.cumulative_probs}")

    def sample(self, num_samples: int = 1000, **kwargs) -> np.ndarray:
        """
        Sample from the target distribution.
        
        For continuous distributions (multidimensional), the following keyword arguments are accepted:
                - init: Initial state, must be a multidimensional numpy array (no default).
                - proposal_cov: Covariance matrix of the candidate distribution (use this if provided).
                - proposal_std: If proposal_cov is not provided, use independent normals for each dimension, with standard deviations defaulting to proposal_std (default 1.0).
                - burn_in: Number of samples during warmup (default 1000).
                - thinning: Sampling interval (default 1).
        
        For discrete and discretized distributions, additional arguments are ignored.
        
        Args:
            num_samples: Required number of samples.
            **kwargs: Additional arguments for continuous sampling.
        
        Returns:
            A numpy array containing the sampling results.
        """
        if self.mode == "continuous":
            return self._sample_continuous(num_samples, **kwargs)
        elif self.mode in ("discrete", "discretized"):
            return self._sample_discrete(num_samples)
        else:
            raise ValueError("Unsupported mode.")

    def _sample_continuous(self, num_samples: int, init: np.ndarray = None,
                             proposal_cov: np.ndarray = None,
                             proposal_std: float = 1.0,
                             burn_in: int = 1000,
                             thinning: int = 1) -> np.ndarray:
        """
        Sample a multidimensional continuous distribution using the Metropolis algorithm.
        
        Args:
            num_samples: The number of samples required.
            init: Initial point, must be a multidimensional numpy array.
            proposal_cov: The candidate distribution covariance matrix. If provided, this matrix is ​​used for sampling.
            proposal_std: If proposal_cov is not provided, the dimensions are assumed to be independent, with standard deviation proposal_std (default 1.0).
            burn_in: The number of samples in the warm-up period (default 1000).
            thinning: The sampling interval (default 1).
        
        Returns:
            np.ndarray, a sample array of shape (num_samples, d).
        """
        if init is None:
            raise ValueError("对于多维连续采样，必须提供初始点 init (numpy array)。")
        x_current = np.array(init)
        d = x_current.shape[0]
        if proposal_cov is not None:
            cov = proposal_cov
        else:
            cov = (proposal_std ** 2) * np.eye(d)

        samples = []
        total_iterations = num_samples * thinning + burn_in
        logger.info(f"Starting multi-dimensional continuous sampling: total_iterations={total_iterations}, init={init}")

        for i in range(total_iterations):
            # 从多维正态分布中生成候选点
            x_candidate = x_current + np.random.multivariate_normal(np.zeros(d), cov)
            # 计算接受率
            p_current = self.target(x_current)
            p_candidate = self.target(x_candidate)
            acceptance_ratio = 1.0 if p_current == 0 else p_candidate / p_current
            if np.random.rand() < min(1, acceptance_ratio):
                x_current = x_candidate
            if i >= burn_in and ((i - burn_in) % thinning == 0):
                samples.append(x_current.copy())
            if (i + 1) % (max(total_iterations // 10, 1)) == 0:
                logger.debug(f"Iteration {i+1}/{total_iterations}: current state = {x_current}")
        return np.array(samples)

    def _sample_discrete(self, num_samples: int) -> np.ndarray:
        """
        For sampling discrete distribution and discretized continuous distribution, the inverse cumulative distribution transformation method is used.

        Args:
            num_samples: The number of samples required.

        Returns:
            np.ndarray，sampling results.
        """
        random_values = np.random.rand(num_samples)
        indices = np.searchsorted(self.cumulative_probs, random_values)
        samples = [self.discrete_values[i] for i in indices]
        return np.array(samples)

    def fit(self, data: np.ndarray) -> Dict[str, Any]:
        """
        Fit data to estimate distribution parameters.
        
        For continuous mode: assume data follows a multivariate normal distribution,
            return sample mean and sample covariance matrix;
        For discrete and discretized modes: count the frequency of each unique value,
            return a normalized probability distribution dictionary.
        
        Args:
            data: multidimensional data array, shape should be (n_samples, d) in continuous mode,
            each row represents a sample (d-dimensional values) in discrete mode.
        
        Returns:
            A dictionary containing the fitting results.
        """
        if self.mode == "continuous":
            # 检查 data 是否为二维数组
            if data.ndim != 2:
                raise ValueError("对于连续模式，data 必须为二维数组 (n_samples, d)")
            mean = np.mean(data, axis=0)
            covariance = np.cov(data, rowvar=False)
            return {"mean": mean, "covariance": covariance}
        elif self.mode in ("discrete", "discretized"):
            # 对于离散数据，我们统计每个唯一值的出现频率
            # data 可以为 (n_samples, d) 数组，或者是一维数组（取值为标量或元组）
            if data.ndim == 1:
                # 如果数据为一维，直接统计每个值
                unique_vals, counts = np.unique(data, return_counts=True)
                freq = {val: count / counts.sum() for val, count in zip(unique_vals, counts)}
            else:
                # 对于多维离散数据，每一行代表一个样本，将其转换为 tuple 后再统计
                data_tuples = [tuple(row) for row in data]
                unique_vals, counts = np.unique(data_tuples, return_counts=True)
                total = counts.sum()
                freq = {val: count / total for val, count in zip(unique_vals, counts)}
            return {"frequencies": freq}
        else:
            raise ValueError("Unsupported mode for fitting.")


# ===========================
# 示例用法
# ===========================
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # 示例 1：多维连续分布——2D 高斯混合分布
    def mixture_density_2d(x: np.ndarray) -> float:
        """
        x 为二维向量，构造两个高斯分布混合：
         - 组件1: 均值 [2, 2]，协方差 0.5 * I，权重 0.3；
         - 组件2: 均值 [-2, -2]，协方差 I，权重 0.7。
        """
        x = np.array(x)
        comp1 = 0.3 * np.exp(- np.sum((x - np.array([2, 2]))**2) / (2 * 0.5))
        comp2 = 0.7 * np.exp(- np.sum((x - np.array([-2, -2]))**2) / (2 * 1.0))
        return comp1 + comp2

    sampler_cont_2d = MDSampler(mixture_density_2d)
    samples_cont_2d = sampler_cont_2d.sample(
        num_samples=5000,
        init=np.array([0.0, 0.0]),
        proposal_std=1.0,
        burn_in=1000,
        thinning=1
    )
    plt.figure(figsize=(8, 6))
    plt.scatter(samples_cont_2d[:, 0], samples_cont_2d[:, 1], s=10, alpha=0.5, label="MCMC Samples")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("2D Mixture of Gaussians - Continuous Sampling")
    plt.legend()
    plt.show()

    # 示例 2：多维离散分布——2D 网格上的分布
    discrete_distribution = {
        (0, 0): 1,
        (0, 1): 2,
        (1, 0): 3,
        (1, 1): 4
    }
    sampler_disc_2d = MDSampler(discrete_distribution)
    samples_disc_2d = sampler_disc_2d.sample(num_samples=10000)
    # 将采样结果转换为二维数组（若为元组则转换）
    samples_disc_2d = np.array([list(s) for s in samples_disc_2d])
    plt.figure(figsize=(8, 6))
    plt.hist2d(samples_disc_2d[:, 0], samples_disc_2d[:, 1],
               bins=[np.arange(-0.5, 2, 1), np.arange(-0.5, 2, 1)],
               density=True, cmap='Blues')
    plt.colorbar()
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("2D Discrete Distribution Sampling")
    plt.show()

    # 示例 3：多维离散化的连续分布——对 2D 高斯混合分布在网格上离散化采样
    x_vals = np.linspace(-10, 10, 100)
    y_vals = np.linspace(-10, 10, 100)
    X, Y = np.meshgrid(x_vals, y_vals)
    points = np.column_stack((X.ravel(), Y.ravel()))
    densities = np.array([mixture_density_2d(p) for p in points])
    sampler_disc_cont_2d = MDSampler((points, densities))
    samples_disc_cont_2d = sampler_disc_cont_2d.sample(num_samples=5000)
    plt.figure(figsize=(8, 6))
    plt.scatter(samples_disc_cont_2d[:, 0], samples_disc_cont_2d[:, 1],
                s=10, alpha=0.5, label="Discretized Samples")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("2D Discretized Continuous Distribution Sampling")
    plt.legend()
    plt.show()
