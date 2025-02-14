library(nkFinanceQuantR)
library(rgl)

f <- function(x, y){
  return(4 * (abs(x) ^ y) + (abs(y - x) ^ y) + abs(x^2 + y^2))
}

xs = seq(-1, 1, 0.001)
ys = seq(-1, 1, 0.001)
ms = matrix(10, length(xs), length(ys))
for(i in 1:length(xs))
{
  for(j in 1:length(ys))
  {
    ms[i, j] = f(xs[i], ys[j])
  }
}
mss = ms
ms[which(ms > 1)] = log(ms[which(ms > 1)], exp(2)) + 1
ms[which(ms > 10)] = 10

# Create a 3D perspective plot# Open 3D plotting device
open3d()

# Create the 3D surface plot
persp3d(xs, ys, ms, col = "lightblue", xlab = "X", ylab = "Y", zlab = "f(x, y)", 
        main = "3D plot of f(x, y)", smooth = TRUE)


idkm <- function(n, ...){
  return(sqrt(exp(log(n * n + 1))) -1)
}
plotf.2d(idkm, c(-10, 10))

