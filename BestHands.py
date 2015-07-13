#!/usr/bin/python
__author__ = "Sam Kennerly"
__copyright__ = "Copyright (C) 2012 Sam Kennerly"
__license__ = "BSD (http://creativecommons.org/licenses/BSD/)"
__version__ = "1.0"
"""
Program for statistical tests of FullTilt.py output. Uses SciPy and NumPy for statistical calculation
and PyLab for plotting. Performs both Fisher test and Lyapunov test on shuffle results.
To use, place this file the same directory as the .csv data file. At command prompt, type
python BestHands.py filename.csv
"""

# Copyright (c) 2012 Sam Kennerly. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 


#### Constants ##################

NUM_BINS = 50					# Number of bins for histogram
MIN_HANDS = 15					# Ignore bins containing fewer than this many hands
SUSPECT_LEVEL = 0.05			# 'suspect' p-values less than SUSPECT_LEVEL
REJECT_LEVEL = 0.01				# 'reject' p-values less than REJECT_LEVEL

#### Import statements ##########

import sys
import numpy
import scipy.stats
import pylab
import random
from math import *

#### Functions ##################

# Stores a hand outcome in the appropriate bin.
def bin_me(q, won, bins):
	for k in range(NUM_BINS):
		if ( bin_probs[k] <= q < bin_probs[k+1] ) :		# Find the correct bin.
			bins[k][1] += 1								# Increment number of hands in this bin.
			if won :
				bins[k][0] += 1				# If hand won, increment number of wins in this bin.
			break

#### Global variables ############

bins = numpy.array( [ [0,0] for k in range(NUM_BINS) ] )	# Bins are ordered pairs: [wins, hands]. 
bin_probs = numpy.linspace(0.5,1.0,NUM_BINS+1)		# Array of bin edges
p_values = numpy.zeros(NUM_BINS)					# Array of binomial test p_values
Z_scores = numpy.zeros(NUM_BINS)					# Recentered, rescaled number of wins
surprisals = numpy.zeros(NUM_BINS)					# Surprisal values = -1.0 * log(p_values)

qualifying_hands = 0			# Total number of hands considered
qualifying_bins = 0				# Number of bins with at least MIN_HANDS entries
fisher_chisq = 0.0				# Fisher test statistic
suspects = 0					# Number of suspicious bins
failures = 0					# Number of rejected bins
total_wins = 0					# Number of times the best hand won
total_q = 0.0					# Used to calculate expectation of total_wins
total_sigsqrd = 0.0				# Used to calculate variance of total_wins

#### Main program ################

# Import .csv data file
filename = sys.argv[1]
inputfile = open(filename,'r')

# Use data file to calculate q = p(best hand wins | no split) and store [wins,trials] in bins.
for line in inputfile:
	current_line = line.replace(' ','').split(',')
	if ( current_line[1] == '1' ):				# Only consider trials with exactly 1 winner
		qualifying_hands += 1					# Remember number of trials evaluated
		pwin = float(current_line[7])			# Get p(best hand wins)
		psplit = float(current_line[9])			# Get p(split pot)
		q = pwin / (1.0 - psplit)				# Calculate q = p(best hand wins | no split)
		total_q += q							# Update expectation of total_wins
		total_sigsqrd += q*(1-q) 				# Update variance of total_wins
		won = bool(int(current_line[6]))		# Did best hand win?
		if (won):								# If so, count it as a win
			total_wins += 1
		bin_me(q, won, bins)					# Enter data into bins
		

# Binomial-test all qualifying bins and update Fisher meta-statistic.
for k in range(NUM_BINS):
	kth_wins = bins[k][0]
	kth_trials = bins[k][1]
	if kth_trials >= MIN_HANDS :					# Ignore bins with too few hands
	
		p_values[k] = scipy.stats.binom.cdf(kth_wins, kth_trials, bin_probs[k])		# Find p-values
		if p_values[k] < ( 1.0 - REJECT_LEVEL ) :		# Did p-value fail?
			failures += 1
		elif p_values[k] < ( 1.0 - SUSPECT_LEVEL ) :		# If not, is p-value suspcious?
			suspects += 1
		surprisals[k] = -1.0 * log(p_values[k])		# Calculate surprisal
		fisher_chisq += 2.0 * surprisals[k]			# Update Fisher statistic
		qualifying_bins += 1
		
		Z_scores[k] = kth_wins - ( kth_trials * bin_probs[k] )		# Recenter number of wins
		variance = kth_trials * bin_probs[k] * (1 - bin_probs[k])	# Estimate variance of trials
		Z_scores[k] /= sqrt(variance)								# Rescale number of wins
		
		# Use this to print data for LaTeX tables
		# print bin_probs[k], "&", kth_wins, "&", kth_trials, "&", round(p_values[k],4), "&", round(surprisals[k],4), "\\\\"

	else :
		p_values[k] = None		# null p-value means "ignore this bin; not enough hands"
		surprisals[k] = None	# null surprisal for empty bins
		Z_scores[k] = None		# null Z-score for empty bins

# Calculate Fisher tail probability
fisher_phi = scipy.stats.chisqprob(fisher_chisq, 2*qualifying_bins)

# Calculate bad beat factor
bad_beat_factor = ( total_wins - total_q ) / sqrt( total_sigsqrd )
lyapunov_lambda = scipy.stats.norm.cdf(bad_beat_factor)

#### Print results #########
print
print qualifying_hands, "hands tested."
print
print qualifying_bins, "bins out of", NUM_BINS, "contain at least", MIN_HANDS, "hands."
print "Of these bins,", failures, "failed and", suspects, "are suspicious."
print "Fisher chi-squared statistic is", fisher_chisq
print "Probability of this result of worse is", fisher_phi
if (fisher_phi < REJECT_LEVEL):
	print "Fisher test REJECTS null hypothesis with", round(( 1.0 - fisher_phi ),4) * 100 , "percent confidence."
elif (fisher_phi < SUSPECT_LEVEL):
	print "Fisher test SUSPECTS null hypothesis with", round(( 1.0 - fisher_phi ),4) * 100 , "percent confidence."
else:
	print "Fisher test FAILS TO REJECT null hypothesis."
print
print "The best hand won", total_wins, "times."
print "Expected", round(total_q, 2), "wins with standard deviation", round( sqrt(total_sigsqrd), 2)
print "Bad beat factor is", round(bad_beat_factor,3)
print "Probability of this result or worse is", lyapunov_lambda
if (lyapunov_lambda < REJECT_LEVEL):
	print "Lyapunov test REJECTS null hypothesis with", round(( 1.0 - lyapunov_lambda ),4) * 100 , "percent confidence."
elif (lyapunov_lambda < SUSPECT_LEVEL):
	print "Lyapunov test SUSPECTS null hypothesis with", round(( 1.0 - lyapunov_lambda ),4) * 100, "percent confidence."
else:
	print "Lyapunov test FAILS TO REJECT null hypothesis."
	

#### Plot results ##############
pylab.ion()
q_values = bin_probs[0:NUM_BINS]		# values of p( win | no split ) for x-axis of plots
bar_width = 0.5 / NUM_BINS				# pylab will ruin bar charts if this is not calculated
pylab.subplots_adjust(wspace=0.2, hspace=0.5) 	# Make some extra space between plots.

# Plot Z-scores for all qualifying bins
pylab.subplot(3,1,1)
pylab.bar(q_values, Z_scores, width=bar_width, color='blue')
pylab.plot(q_values, numpy.ones(NUM_BINS),color='green')
pylab.axhline(y=1, color='g')
pylab.axhline(y=-1, color='g')
pylab.axhline(y=2, color='y')
pylab.axhline(y=-2, color='y')
pylab.axhline(y=3, color='r')
pylab.axhline(y=-3, color='r')
pylab.ylabel("Z-score")
pylab.xlim((0.5,1))

# How many hands were in each bin?
pylab.subplot(3,1,2)
pylab.bar(q_values, bins[:,1], width=bar_width, color='purple')
pylab.ylabel("number of hands")
pylab.axhline( y = MIN_HANDS, color='k')
pylab.xlim((0.5,1))

# How surprisingly bad are the results? (0 is very lucky, 1.0 is ordinary, >> 1 is unlucky.)
pylab.subplot(3,1,3)
pylab.bar(q_values, surprisals, width=bar_width, color='red')
pylab.xlabel("P( best hand wins | no split )")
pylab.ylabel("surprisal")
pylab.xlim((0.5,1))

# This is a trick for keeping the plot window open.
raw_input("\nPress Enter to quit.\n")
pylab.ioff()
