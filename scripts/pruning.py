# pruning.py

''' 
take a network made by string_chem_net, designate some input and output
metabolites, do fba to find reaction fluxes, drop all reactions with no flux,
and then do two things:

1. remove the smallest flux, make sure that doesn't render the solution
infeasible, and then iterating this process until you can't remove a reaction

2. remove a reaction at random, make sure that doesn't render the solution
infeasible, then repeat until you can't remove a reaction
 
note that the first method will always give the same result while the second
is liable to give a range of results in many (but not all) cases, so this
script does the second approach a bunch of times but only does the first one
once per call
'''

import sys
import string_chem_net as scn
import random
import re
import pandas as pd

# count number of 1s in a bitstring
def count_bitstring(bitstring):
    count = 0
    for bit in [int(bit) for bit in list(bitstring)]:
        if bit == 1:
            count += 1
    return(count)

# get command-line arguments
try:
    (monos, max_pol, ins, outs, reps) = sys.argv[1:]
except ValueError:
    sys.exit('Arguments: monomers, max polymer length, number of food sources, \
number of biomass precursors, number of times to prune each network.'
    )

print('Creating universal string chemistry network.')
SCN = scn.CreateNetwork(monos, int(max_pol))
cobra_model = scn.make_cobra_model(SCN.met_list, SCN.rxn_list)
scn.reverse_rxns(cobra_model, len(cobra_model.reactions))
scn.choose_inputs(int(ins), cobra_model)
bm_rxn = scn.choose_bm_mets(int(outs), cobra_model)
cobra_model.objective = bm_rxn

# make sure that there's at least one feasible solution before trying to prune
solution = cobra_model.optimize()
i = 0
while solution.status == 'infeasible' or (solution.fluxes == 0).all():
    # remove existing biomass and input reactions
    cobra_model.remove_reactions([bm_rxn])
    cobra_model.remove_reactions(cobra_model.boundary)
    # choose new ones and see if those yield a solvable network
    scn.choose_inputs(int(ins), cobra_model)
    bm_rxn = scn.choose_bm_mets(int(outs), cobra_model)
    cobra_model.objective = bm_rxn
    solution = cobra_model.optimize()

print('Pruning network.')
min_flux_pruned = scn.min_flux_prune(cobra_model)
min_flux_count = len(min_flux_pruned.reactions)
min_flux_bitstring = scn.make_bitstring(cobra_model, min_flux_pruned)

# will hold number of reactions in each network after reps runs of random_prune
random_pruned_counts = list()
# will hold bitstrings of all unique reactions and the count of times each one
# came up
random_pruned_dict = dict()
# will hold all the unique networks found by random_prune after reps runs
random_pruned_nets = list()
for i in range(1, int(reps)):
    if i % 100 == 0:
        print(f'On random prune {i}.')
    pruned_net = scn.random_prune(cobra_model, bm_rxn)
    # in order to know whether we've seen this model before, we can't just 
    # compare models, since no two models are ever 'equal', so we'll compare
    # reaction presence bitstrings. 
    # We also want to keep track of how many times we see each model, so we 
    # will make a dict with the bitstrings as keys
    # sort is in-place
    bitstring = scn.make_bitstring(cobra_model, pruned_net)
    if bitstring not in random_pruned_dict.keys():
        # make sure all reaction lists are sorted so that all isomorphic
        # networks have the same reaction list
        random_pruned_dict[bitstring] = 1
        random_pruned_nets.append(pruned_net)
    else:
        # if we already found this network once, then increment the counter
        # in random_pruned_nets by 1
        random_pruned_dict[bitstring] += 1
    # so that we can see the distribution of network sizes, record the length
    # of the reaction list each time, regardless of whether or not we've seen
    # this network before
    random_pruned_counts.append(len(pruned_net.reactions))

print('Preparing output.')
# make a dataframe of all the bitstrings we've generated
# turn the dictionary into a list of lists before coercion
bitstring_df = pd.DataFrame(list(map(list, random_pruned_dict.items())))
# add the bitstring from the min flux prune
bitstring_df = bitstring_df.append(
    pd.Series([min_flux_bitstring, 1]), ignore_index = True
)
# name columns
bitstring_df.columns = ['bitstring', 'occurrences']
# add in a column for the number of reactions in each network 
bitstring_df['rxn_count'] = list(map(count_bitstring, bitstring_df.bitstring))
# write output
bitstring_df.to_csv(
    f'../data/{monos}_{max_pol}_{ins}ins_{outs}outs_{reps}reps.csv'
)