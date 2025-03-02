# universal_sampler.py

# des
#
# An versatile sampling library for distributions, supporting three cases:
 
# Continuous distribution: pass a callable object target(x), return the unnormalized probability density value;
# Discrete distribution: pass a dictionary or list of [(value, weight), ...];
# Discretized continuous distribution: pass a pair (points, densities), representing the support points and corresponding unnormalized densities respectively.

import numpy as np
from typing import Callable, List, Union, Dict, Any
import logging

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DSampler:
    """
    General distribution sampler.
    
    Supports three modes:
    - continuous: continuous distribution, input is the target density function (unnormalized).
    - discrete: discrete distribution, input is a dictionary or a list of [(value, weight), ...].
    - discretized: discretized continuous distribution, input is a (points, densities) pair.
    """

    def __init__(self, target: Union[
        Callable[[float], float],
        Dict[Any, float],
        List[Any],
        tuple
    ]):
        """
        Initialize the sampler.
        
        Args:
        target:
        - If it is a callable object, it is regarded as the target density function of the continuous distribution;
        - If it is a dictionary, the key is a discrete value and the value is the corresponding probability or weight;
        - If it is a list, the judgment format is:
        * If each element in the list is a (value, weight) pair, it is a discrete distribution;
        * If the list length is 2 and they are points and densities respectively, it is a discretized continuous distribution;
        - If it is a tuple and the length is 2, it is regarded as a discretized continuous distribution of (points, densities).
        """
        self.target = target
        if callable(target):
            self.mode = "continuous"
            logger.info("Initialized in continuous mode.")
        elif isinstance(target, dict):
            self.mode = "discrete"
            self._prepare_discrete_from_dict()
            logger.info("Initialized in discrete mode from dict.")
        elif isinstance(target, tuple):
            # 视为 (points, densities)
            if len(target) == 2:
                self.mode = "discretized"
                self._prepare_discretized()
                logger.info("Initialized in discretized mode from tuple.")
            else:
                raise ValueError("Tuple input must have length 2: (points, densities).")
        elif isinstance(target, list):
            # 若列表长度为2且元素不是成对的 (value, weight)，则认为是 (points, densities)
            if len(target) == 2 and not (all(isinstance(item, (list, tuple)) and len(item) == 2 for item in target)):
                self.mode = "discretized"
                self._prepare_discretized()
                logger.info("Initialized in discretized mode from list of two elements.")
            elif all(isinstance(item, (list, tuple)) and len(item) == 2 for item in target):
                self.mode = "discrete"
                self.target = dict(target)
                self._prepare_discrete_from_dict()
                logger.info("Initialized in discrete mode from list of pairs.")
            else:
                raise ValueError("List input format not recognized.")
        else:
            raise ValueError("Unsupported target type. Must be callable, dict, list, or tuple.")

    def _prepare_discrete_from_dict(self):
        """
        Preprocess the discrete distribution (in dictionary form):
        - Normalize the weights;
        - Construct the cumulative distribution for sampling.
        """
        values = list(self.target.keys())
        probs = np.array([self.target[v] for v in values], dtype=float)
        total = probs.sum()
        if total <= 0:
            raise ValueError("Sum of probabilities must be positive.")
        probs = probs / total
        self.discrete_values = values
        self.discrete_probs = probs
        self.cumulative_probs = np.cumsum(probs)
        logger.debug(f"Discrete cumulative probabilities: {self.cumulative_probs}")

    def _prepare_discretized(self):
        """
        Preprocess the discretized continuous distribution:
        - target should be in the form of (points, densities);
        - Normalize the density and construct the cumulative distribution for sampling.
        """
        # Suppoer Point
        points = np.asarray(self.target[0])
        densities = np.asarray(self.target[1], dtype=float)
        if points.shape[0] != densities.shape[0]:
            raise ValueError("Points and densities must have the same length.")
        total = densities.sum()
        if total <= 0:
            raise ValueError("Sum of densities must be positive.")
        probs = densities / total
        self.discrete_values = points
        self.discrete_probs = probs
        self.cumulative_probs = np.cumsum(probs)
        logger.debug(f"Discretized cumulative probabilities: {self.cumulative_probs}")

    def sample(self, num_samples: int = 1000, **kwargs) -> np.ndarray:
        """
        Sample from the target distribution.
        
        For continuous distributions, the following keyword arguments are accepted:
        - init: initial state (default 0.0)
        - proposal_std: standard deviation of the candidate distribution (default 1.0)
        - burn_in: number of samples to sample during warmup (default 1000)
        - thinning: sampling interval (default 1)
        
        For discrete and discretized distributions, additional arguments are ignored.
        
        Args:
        num_samples: number of samples to sample.
        **kwargs: other arguments for continuous sampling.
        
        Returns:
        numpy array containing the sampling results.
        """
        if self.mode == "continuous":
            return self._sample_continuous(num_samples, **kwargs)
        elif self.mode in ("discrete", "discretized"):
            return self._sample_discrete(num_samples)
        else:
            raise ValueError("Unsupported mode.")

    def _sample_continuous(self, num_samples: int, init: float = 0.0, proposal_std: float = 1.0,
                             burn_in: int = 1000, thinning: int = 1) -> np.ndarray:
        """
        Sampling continuous distribution using Metropolis algorithm.
        
        Args:
        num_samples: The number of samples required.
        init: Initial value (default 0.0).
        proposal_std: Standard deviation of the candidate distribution (default 1.0).
        burn_in: Number of samples in warm-up period (default 1000).
        thinning: Sampling interval (default 1).
        
        Returns:
        np.ndarray, containing the sampling result.
        """
        samples = []
        x_current = init
        total_iterations = num_samples * thinning + burn_in
        logger.info(f"Starting continuous sampling: total_iterations={total_iterations}, "
                    f"init={init}, proposal_std={proposal_std}")

        for i in range(total_iterations):
            # 生成候选值（对称正态候选分布）
            x_candidate = x_current + np.random.normal(0, proposal_std)

            # 计算接受率
            p_current = self.target(x_current)
            p_candidate = self.target(x_candidate)
            acceptance_ratio = 1.0 if p_current == 0 else p_candidate / p_current

            if np.random.rand() < min(1, acceptance_ratio):
                x_current = x_candidate

            if i >= burn_in and ((i - burn_in) % thinning == 0):
                samples.append(x_current)

            if (i + 1) % (total_iterations // 10) == 0:
                logger.debug(f"Iteration {i+1}/{total_iterations}: current state = {x_current}")

        return np.array(samples)

    def _sample_discrete(self, num_samples: int) -> np.ndarray:
        """
        Sample discrete and discretized distributions using the inverse cumulative distribution transform method.
        
        Args:
        num_samples: The number of samples required.
        
        Returns:
        np.ndarray containing the sampled results.
        """
        random_values = np.random.rand(num_samples)
        indices = np.searchsorted(self.cumulative_probs, random_values)
        samples = np.array([self.discrete_values[i] for i in indices])
        return samples

    def fit(self, data: np.ndarray) -> Dict[str, Any]:
        """
        Fit data to estimate distribution parameters (for future expansion).
        
        This method is a placeholder function. In production applications,
        you can implement parameter estimation of specific distributions as needed (such as maximum likelihood estimation, Bayesian inference, etc.).
        
        Args:
        data: One-dimensional data array.
        
        Returns:
        A dictionary containing the fitting results.
        """
        raise NotImplementedError("Fitting method not implemented. Use specialized fitting functions.")


# ===========================
# Example
# ===========================
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # 示例 1：连续分布——混合高斯分布（目标密度函数）
    def mixture_density(x: float) -> float:
        comp1 = 0.3 * np.exp(- (x - 2) ** 2 / (2 * 0.5))
        comp2 = 0.7 * np.exp(- (x + 2) ** 2 / (2 * 1.0))
        return comp1 + comp2

    sampler_cont = DSampler(mixture_density)
    samples_cont = sampler_cont.sample(
        num_samples=5000,
        init=0.0,
        proposal_std=1.0,
        burn_in=1000,
        thinning=1
    )
    plt.figure(figsize=(8, 5))
    plt.hist(samples_cont, bins=50, density=True, alpha=0.6, label="MCMC Samples")
    x_vals = np.linspace(-10, 10, 1000)
    y_vals = mixture_density(x_vals)
    y_vals_norm = y_vals / np.trapz(y_vals, x_vals)
    plt.plot(x_vals, y_vals_norm, 'r-', lw=2, label="Target Distribution")
    plt.xlabel("x")
    plt.ylabel("Density")
    plt.title("Sampling from a Mixture of Gaussians (Continuous)")
    plt.legend()
    plt.show()

    # 示例 2：离散分布——骰子（字典或列表形式）
    dice_distribution = {'1': 1, '2': 1, '3': 1, '4': 1, '5': 1, '6': 1}
    sampler_disc = DSampler(dice_distribution)
    samples_disc = sampler_disc.sample(num_samples=10000)
    samples_disc_int = np.array([int(s) for s in samples_disc])
    plt.figure(figsize=(8, 5))
    plt.hist(samples_disc_int, bins=np.arange(1, 8) - 0.5, density=True, alpha=0.6, label="Discrete Samples")
    plt.xticks(range(1, 7))
    plt.xlabel("Dice Face")
    plt.ylabel("Probability")
    plt.title("Sampling from a Uniform Dice Distribution (Discrete)")
    plt.legend()
    plt.show()

    # 示例 3：离散化的连续分布
    # 例如：对混合高斯分布在一组离散点上评估密度
    points = np.linspace(-10, 10, 200)
    densities = mixture_density(points)  # 非归一化密度
    sampler_disc_cont = Sampler((points, densities))
    samples_disc_cont = sampler_disc_cont.sample(num_samples=5000)
    plt.figure(figsize=(8, 5))
    plt.hist(samples_disc_cont, bins=50, density=True, alpha=0.6, label="Discretized Samples")
    plt.plot(x_vals, y_vals_norm, 'r-', lw=2, label="Original Continuous Distribution")
    plt.xlabel("x")
    plt.ylabel("Density")
    plt.title("Sampling from a Discretized Continuous Distribution")
    plt.legend()
    plt.show()
