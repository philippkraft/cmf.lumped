import spotpy
import spotpy.describe
import os


def parallel_auto():
    """
    Returns 'mpi', if this code runs with MPI, else returns 'seq'
    :return:
    """
    return 'mpi' if 'OMPI_COMM_WORLD_SIZE' in os.environ else 'seq'


def get_runs(default=1):
    """
    Returns the number of runs, given by commandline or variable
    :param default: Return this if no other source for number of runs has been found
    :return: int
    """
    # Get number of runs
    if 'SPOTPYRUNS' in os.environ:
        # from environment
        return int(os.environ['SPOTPYRUNS'])
    else:
        # run once
        return default


def sample(model, runs, algname='lhs', save_threshold=None, dbformat='hdf5', parallel=None):
    runs = get_runs(runs)
    alg = getattr(spotpy.algorithms, algname)
    sampler = alg(
        model, sim_timeout=600,
        dbname=str(model), dbformat=dbformat, parallel=parallel or parallel_auto(), save_threshold=save_threshold)
    print(spotpy.describe.sampler(sampler))
    print(spotpy.describe.setup(model))
    sampler.sample(runs)
