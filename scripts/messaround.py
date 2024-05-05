import string_chem_net_core as scn

monos = 'ab' # characters to use as monomers
max_len = 5  # maximum length of each string chemical

SCN = scn.CreateNetwork(monos, max_len)