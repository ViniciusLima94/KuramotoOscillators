### Imports

import matplotlib.pyplot as plt
import scipy
import jax
import numpy as np
import xarray as xr
from mne.time_frequency.tfr import tfr_array_morlet
from hoi.core import get_mi
from frites.core import copnorm_nd

### Load data

data = scipy.io.loadmat("kuramoto_matlab.mat")["data"]
print(data.shape)

ntrials = 500
fs = 600
time = np.arange(-0.5, 1 + 1 / fs, 1 / fs)
CS = np.linspace(1, 100, ntrials)

### Convert to xarray

data = xr.DataArray(
    data.transpose(1, 0, 2),
    dims=("trials", "roi", "times"),
    coords=(CS, range(3), time),
)

### Decompose in time-frequency domain

freqs = np.linspace(10, 80, 50)

S = tfr_array_morlet(
    data.values,
    fs,
    freqs,
    freqs / 7,
    output="complex",
    n_jobs=10,
    zero_mean=False,
)

S = xr.DataArray(
    S,
    dims=("trials", "roi", "freqs", "times"),
    coords={"freqs": freqs, "times": data.times.values},
)

### Compute phase and amplitude terms

# Define the function to compute MI using HOI and JAX
mi_fcn = get_mi("gc")

# vectorize the function to first and second dimension
gcmi = jax.vmap(jax.vmap(mi_fcn, in_axes=0), in_axes=0)

# Select data for nodes
x = S.sel(roi=[0]).data.squeeze()
y = S.sel(roi=[1]).data.squeeze()
z = S.sel(roi=[2]).data.squeeze()

# Edge activity (with and without normalisation)
e1 = x * np.conj(y)
e2 = y * np.conj(z)
e3 = x * np.conj(z)

# Real and Imag parts pf edge activity
e1r, e1i = np.real(e1), np.imag(e1)
e2r, e2i = np.real(e2), np.imag(e2)
e3r, e3i = np.real(e3), np.imag(e3)

# Stack complex values
E1 = np.stack((e1r, e1i), axis=1)
E2 = np.stack((e2r, e2i), axis=1)
E3 = np.stack((e3r, e3i), axis=1)
E12 = np.stack((e1r, e1i, e2r, e2i), axis=1)
E23 = np.stack((e2r, e2i, e3r, e3i), axis=1)
E123 = np.stack((e1r, e1i, e2r, e2i, e3r, e3i), axis=1)

# Swap axis 0 with 3 and 1 with 2
E1 = np.moveaxis(E1, [0, 1], [-1, -2])
E2 = np.moveaxis(E2, [0, 1], [-1, -2])
E3 = np.moveaxis(E3, [0, 1], [-1, -2])
E12 = np.moveaxis(E12, [0, 1], [-1, -2])
E23 = np.moveaxis(E23, [0, 1], [-1, -2])
E123 = np.moveaxis(E123, [0, 1], [-1, -2])

# Stims across trials
stim = data.trials.values
stim = np.expand_dims(stim, axis=(0, 1))
stim = np.tile(stim, (len(freqs), data.sizes["times"], 1, 1))

# # MI frequency domain
# mi_freq[i, :] = gcmi_nd_cc(X, Y, mvaxis=1, traxis=0)

# # Coherence
# coh[i, :] = np.abs(e1.mean(axis=0)).squeeze()

# # Phase-Locking Value
# plv[i, :] = np.abs(e1n.mean(axis=0)).squeeze()

# Copnorm
E1 = copnorm_nd(E1, axis=-1)
E2 = copnorm_nd(E2, axis=-1)
E3 = copnorm_nd(E3, axis=-1)
E12 = copnorm_nd(E12, axis=-1)
E23 = copnorm_nd(E23, axis=-1)
E123 = copnorm_nd(E123, axis=-1)
stim = copnorm_nd(stim, axis=-1)

# MIF for edge encoding
mif_e1 = gcmi(E1, stim).T
mif_e2 = gcmi(E2, stim).T
mif_e3 = gcmi(E3, stim).T
mif_e12 = gcmi(E12, stim).T
mif_e23 = gcmi(E23, stim).T
mif_e123 = gcmi(E123, stim).T

red = np.minimum(mif_e1, mif_e2)

syn = mif_e123 - np.maximum(mif_e1, mif_e2)

### Plot

times = data.times.values
ax = plt.subplot()
# Plot single-trial and time-frequency MI
mi = xr.DataArray(mif_e3, dims=("times", "freqs"), coords=(times, freqs))
# Plot trial-average time-frequency MI
mi.plot(x="times", y="freqs", cmap="viridis", vmin=0)
# mi.plot.title('ciao')
ax.set_title(
    "Coherence between node 2 and 3 using Frequency-domain MI (Kuramoto Chain)"
)
ax.set_xlabel("Time (samples)")
ax.set_ylabel("Frequency (Hz)")
plt.show()

ax = plt.subplot()
# Plot single-trial and time-frequency MI
mi = xr.DataArray(mif_e123, dims=("times", "freqs"), coords=(times, freqs))
# Plot trial-average time-frequency MI
mi.plot(x="times", y="freqs", cmap="viridis", vmin=0)
# mi.plot.title('ciao')
ax.set_title("Total MI I(e1, e2; coupling)")
ax.set_xlabel("Time (samples)")
ax.set_ylabel("Frequency (Hz)")
plt.show()

ax = plt.subplot()
# Plot single-trial and time-frequency MI
mi = xr.DataArray(red, dims=("times", "freqs"), coords=(times, freqs))
# Plot trial-average time-frequency MI
mi.plot(x="times", y="freqs", cmap="viridis", vmin=0)
# mi.plot.title('ciao')
ax.set_title("Redundancy")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Frequency (Hz)")
plt.show()

ax = plt.subplot()
# Plot single-trial and time-frequency MI
mi = xr.DataArray(syn, dims=("times", "freqs"), coords=(times, freqs))
# Plot trial-average time-frequency MI
mi.plot(x="times", y="freqs", cmap="viridis", vmin=0)
# mi.plot.title('ciao')
ax.set_title("Synergy")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Frequency (Hz)")
plt.show()