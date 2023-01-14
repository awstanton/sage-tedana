import numpy as np


def _get_shr_mem_keys(mask, delta, r2star_res, s0_I_res, r2_res, rmspe_res):
    shr_mem_keys = {
        "Y": None,
        "X": None,
        "r2star_guess": None,
        "s0_I_guess": None,
        "r2_guess": None,
        "s0_II_guess": None,
        "delta": delta,
        "r2star_res": r2star_res[mask, :],
        "s0_I_res": s0_I_res[mask, :],
        "r2_res": r2_res[mask, :],
        "s0_II_res": None,
        "rmspe_res": rmspe_res[mask, :],
    }
    return shr_mem_keys


def _get_model(i_v, i_t, delta):
    delta = delta[i_v, i_t]

    def _three_param(X, r2star, s0_I, r2):
        res = np.zeros(X.shape)

        res[X < X[-1] / 2] = s0_I * np.exp(-1 * X[X < X[-1] / 2] * r2star)
        res[X > X[-1] / 2] = (
            (1 / delta)
            * np.exp(-1 * X[-1] * (r2star - r2))
            * np.exp(-1 * X[X > X[-1] / 2] * ((2 * r2) - r2star))
            * (s0_I)
        )
        return res

    return _three_param


def _get_max_iter(arrs_shr_mem):
    if arrs_shr_mem["s0_II_guess"] is None:
        return 10000
    else:
        return 1000


def _get_guesses(i_v, i_t, arrs_shr_mem):
    return (
        arrs_shr_mem["r2star_guess"][i_v, i_t],
        arrs_shr_mem["s0_I_guess"][i_v, i_t],
        arrs_shr_mem["r2_guess"][i_v, i_t],
    )


def _eval_model(i_v, i_t, X, arrs_shr_mem, model):
    return model(
        X,
        arrs_shr_mem["r2star_res"][i_v, i_t],
        arrs_shr_mem["s0_I_res"][i_v, i_t],
        arrs_shr_mem["r2_res"][i_v, i_t],
    )


def _get_bounds(arrs_shr_mem):
    return (
        (0.1, 0, 0.1),
        (10000, np.inf, 10000),
    )


def fit_nonlinear_3param():
    r2star_res, s0_I_res, r2_res, s0_II_res, rmspe_res = _init_maps()

    t2star_guess, s0_I_guess, t2_guess, _, delta_guess, _ = get_guesses(data, tes, mask)

    mask = mask.reshape(mask.shape[0])

    Y = data[mask, :, :]
    X = tes

    # these must match the function signature of fit_nonlinear_sage
    shr_mem_keys = nonlinear_4param_sage._get_shr_mem_keys(
        mask,
        Y,
        X,
        r2star_guess,
        s0_I_guess,
        r2_guess,
        s0_II_guess,
        r2star_res,
        s0_I_res,
        r2_res,
        s0_II_res,
        rmspe_res,
    )

    shr_mems, arrs_shr_mem = concurrency_sage._prep_shared_mem(shr_mem_keys)

    kwargs = {key: (value.name if value is not None else None) for key, value in shr_mems.items()}

    concurrency_sage._start_and_join_procs(Y.shape[0], n_echos, n_vols, dtype, kwargs)

    r2star_guess = arrs_shr_mem["r2star_res"]
    s0_I_guess = arrs_shr_mem["s0_I_res"]
    r2_guess = arrs_shr_mem["r2_res"]
    delta = np.divide(arrs_shr_mem["s0_I_res"], arrs_shr_mem["s0_II_res"])
    delta[np.logical_or(delta < -9, delta > 11)] = 1
    delta[np.isnan(delta)] = 1

    r2star_res = np.zeros((n_samps, n_vols))
    s0_I_res = np.zeros((n_samps, n_vols))
    r2_res = np.zeros((n_samps, n_vols))
    rmspe_res = np.zeros((n_samps, n_vols))

    shr_mem_keys_3param = _get_shr_mem_keys()

    shr_mems_3param, arrs_shr_mem_3param = concurrency_sage._prep_shared_mem(shr_mem_keys_3param)

    kwargs_3param = {
        key: (value.name if value is not None else None) for key, value in shr_mems_3param.items()
    }
    kwargs_3param.update(
        {
            "Y": kwargs["Y"],
            "X": kwargs["X"],
            "r2star_guess": kwargs["r2star_res"],
            "s0_I_guess": kwargs["s0_I_res"],
            "r2_guess": kwargs["r2_res"],
        }
    )

    _start_and_join_procs(Y.shape[0], n_echos, n_vols, dtype, fittype, kwargs_shm_3param)

    r2star_res, s0_I_res, r2_res, s0_II_res, delta, rmspe_res = utils_sage._unmask_and_copy(
        arrs_shr_mem_3param, mask
    )

    for shm in shr_mems_3param.values():
        if shm is not None:
            shm.close()
            shm.unlink()

    r2star_res, s0_I_res, r2_res, s0_II_res, delta, rmspe_res = utils_sage._unmask_and_copy(
        arrs_shr_mem, mask
    )

    for shm in shr_mems.values():
        if shm is not None:
            shm.close()
            shm.unlink()

    t2star_res = 1 / r2star_res
    t2_res = 1 / r2_res

    return t2star_res, s0_I_res, t2_res, s0_II_res, delta, rmspe_res
