# many_min_prunes.py
# runs the minimum flux pruning algorithm on a bunch of networks and 
# compares the results

import sys
import string_chem_net as scn
import pandas as pd

# get command-line arguments
try:
    (monos, max_pol, ins, outs, reps) = sys.argv[1:]
except ValueError:
    sys.exit('Arguments: monomers, max polymer length, number of food sources, \
number of biomass precursors, number of times to reselect food sources.')

# create the reference network and pick some food sources and a biomass rxn
SCN = scn.CreateNetwork(monos, int(max_pol))
cobra_model = scn.make_cobra_model(SCN.met_list, SCN.rxn_list)
scn.reverse_rxns(cobra_model, len(cobra_model.reactions))
scn.choose_inputs(int(ins), cobra_model)
bm_rxn = scn.choose_bm_mets(int(outs), cobra_model)
print(f'Biomass reaction: {bm_rxn.id}')
cobra_model.objective = bm_rxn

i = 0
# record all of the food metabolites that were used
food_mets = list()
bitstrings = list()
# use a while loop and not a for loop so we can go back on occasion
while i < int(reps):
    i = i + 1
    foods_string = ' '.join([met.id for met in cobra_model.boundary])
    print(f'Food source group {i}: {foods_string}')
    # choose some new food sources (remove existing ones)
    cobra_model.remove_reactions(cobra_model.boundary)
    scn.choose_inputs(int(ins), cobra_model, bm_rxn)
    # see if this choice of metabolites can produce the biomass on this network
    solution = cobra_model.optimize()
    bm_rxn_flux = solution.fluxes.get(key = bm_rxn.id)
    if solution.status == 'infeasible' or bm_rxn_flux < 1e-10:
        print('There were no feasible solutions; reselecting food sources.')
        # redo this iteration of the loop
        i = i - 1
        continue
    # record the metabolites that worked and prune the network
    else:
        food_mets.append('-'.join([met.id for met in cobra_model.boundary]))
        pruned_net = scn.min_flux_prune(cobra_model)
        bitstring = scn.make_bitstring(cobra_model, pruned_net)
        bitstrings.append(bitstring)

# make a dataframe out of the two lists
bitstring_df = pd.DataFrame(list(zip(food_mets, bitstrings)))
bitstring_df.columns = ['inputs','bitstring']
bitstring_df.to_csv(
    f'data/{monos}_{max_pol}_{reps}x{ins}ins_{outs}outs.csv'
)