import numpy as np

# %%
perms = np.genfromtxt('LocationPerms.csv', delimiter=',')
# %%
a = perms.reshape((perms.shape[0], perms.shape[1] // 4, perms.shape[1] // 3),order='F')
