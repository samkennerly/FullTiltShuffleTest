#!/usr/bin/env python
__author__ = "Alfred Whitehead"
__copyright__ = "Copyright (C) 2009 Alfred Whitehead"
__license__ = "BSD (http://creativecommons.org/licenses/BSD/)"
__version__ = "0.1" 
"""
Program for parsing Full Tilt Poker log files, and generating a list of
probabilities that observed events actually occurred.  Limited to looking at
hands where two plays are "heads-up" (no other players, at least one player
all-in) before the flop.  All other hands are filtered out.
"""


# Copyright (c) 2009, Alfred Whitehead
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 

import re, glob
import cPickle as pickle
from pokereval import PokerEval

pokerev = PokerEval()

card_order = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
hand_class_order = []
probability_cache = {}

def get_headsup_probabilities(hand1, hand2):
    """ Returns a tuple of (best_hand_index, p_best_wins, p_worst_wins, p_tie).
    If the result is in the cache, the cached value is returned.  If not, the
    probabilities are calculated using exhaustive search and then added to the
    cache. """
    global probability_cache
    prob_tuple = False
    if probability_cache.has_key(hand1):
        if probability_cache[hand1].has_key(hand2):
            prob_tuple = probability_cache[hand1][hand2]
    elif probability_cache.has_key(hand2):
        if probability_cache[hand2].has_key(hand1):
            prob_tuple = probability_cache[hand2][hand1]
    if not prob_tuple:
        global pokerev
        hands_pokereval = []
        for hand in [hand1, hand2]:
            hands_pokereval.append(hand.split())
        ev = pokerev.poker_eval(game='holdem', pockets=hands_pokereval,
                                board=['__','__','__','__','__'])
        N = ev['info'][0]
        hand_stats = ev['eval']
        favoured_hand = False
        if hand_stats[0]['winhi'] >= hand_stats[1]['winhi']:
            favoured_hand = 0
        else:
            favoured_hand = 1
        unfavoured_hand = abs(favoured_hand-1)
        p_favoured_wins = float(hand_stats[favoured_hand]['winhi']) / float(N)
        p_favoured_loses = float(hand_stats[favoured_hand]['losehi']) / float(N)
        p_tie = float(hand_stats[favoured_hand]['tiehi']) / float(N)
        prob_tuple = (favoured_hand, p_favoured_wins, p_favoured_loses, p_tie)
        if probability_cache.has_key(hand1):
            assert not probability_cache[hand1].has_key(hand2), "Generated a probability for something we already knew (h2)."
            probability_cache[hand1][hand2] = prob_tuple
        elif probability_cache.has_key(hand2):
            assert not probability_cache[hand2].has_key(hand1), "Generated a probability for something we already knew (h1)."
            probability_cache[hand2][hand1] = prob_tuple
        else:
            if favoured_hand == 0:
                probability_cache[hand1] = {}
                probability_cache[hand1][hand2] = prob_tuple
            else:
                probability_cache[hand2] = {}
                probability_cache[hand2][hand1] = prob_tuple
    return prob_tuple

def load_probability_cache(filename='probability_cache.pickle'):
    """ Loads up the probability cache from a given Pickle file.  This operation
    destroys any data already in the probability cache.  If the file doesn't
    exist, the probability cache is unchanged.  """
    global probability_cache
    try:
        f = open(filename, 'r')
        probability_cache = pickle.load(f)
        f.close()
    except:
        pass

def save_probability_cache(filename='probability_cache.pickle'):
    """ Saves the contents of the probability cache to disk.  Overwrites the
    file.  """
    global probability_cache
    f = open(filename, 'w')
    pickle.dump(probability_cache, f)
    f.close()

def card_rank(card):
    """ Returns an integer for the card's numerical rank.  Ace = 13, Duece = 1.
    """
    return 13 - card_order.index(card)

def classify_hand(hand):
    """ Classifies the hand by its more generic category (ie: Ah Kh -> AK s) """
    card1 = hand[0]
    suit1 = hand[1]
    card2 = hand[3]
    suit2 = hand[4]
    classification = ''
    if card_rank(card1) >= card_rank(card2):
        classification = '%s%s' % (card1, card2)
    else:
        classification = '%s%s' % (card2, card1)
    if suit1 == suit2:
        classification += ' s'
    return classification

def compare_hands(h1, h2):
    """ Compares two hands by their hand class.  Returns -1, 0, or 1 if the left
    hand is better, equal to, worse than the right hand.  "Better" is determined
    by the single-hand odds for its hand class (ie: AA > AK s) """
    return compare_hand_classes(classify_hand(h1), classify_hand(h2))

def compare_hand_classes(hc1, hc2):
    """ Compares two hand classes (ie: AA vs AK s) and returns -1, 0, or 1 if
    the left hand class is favoured over the right.  Favoured determined by
    single-hand odds. """
    hc1i = hand_class_order.index(hc1)
    hc2i = hand_class_order.index(hc2)
    if hc1i < hc2i: 
        return -1
    elif hc1i == hc2i:
        return 0
    else:
        return 1

def sort_hands(hands):
    """ Sort an array of hands by single-hand win probability. """
    hands.sort(compare_hands)

def evaluate_result(hands, winners, winning_hand):
    """ Prints CSV a line describing the analysis of these hands. """
    if winners == len(hands):
        winning_hand = "Draw"
    out_s = ""
    out_s += "%s, " % (winning_hand)
    out_s += str(winners) + ", "
    if len(hands) == 2:
        (favoured_hand, p_favoured_wins, p_favoured_loses, p_tie) = \
                get_headsup_probabilities(hands[0], hands[1])
        unfavoured_hand = abs(favoured_hand-1)
        fhcl = classify_hand(hands[favoured_hand])
        uhcl = classify_hand(hands[unfavoured_hand])
        favoured_won = 0
        if winning_hand == hands[favoured_hand]:
            favoured_won = 1
        p_this_outcome = 0.0
        if favoured_won:
            p_this_outcome = p_favoured_wins
        elif winning_hand == 'Draw':
            p_this_outcome = p_tie
        else:
            p_this_outcome = p_favoured_loses
        sum_ps = p_favoured_wins + p_favoured_loses + p_tie
        out_s += '%s,%s,%s,%s,%d,%.12f,%.12f,%.12f,%.12f,%.12f,' % (hands[favoured_hand], \
            hands[unfavoured_hand], fhcl, uhcl, favoured_won, p_favoured_wins, \
            p_favoured_loses, p_tie, p_this_outcome, sum_ps)
    else:
        out_s += ',,,,,,,,,,,'
    
    sort_hands(hands)
    out_s += ", ".join(hands)
    print out_s
    return out_s

def main():
    """ Main program flow here. """
    f = open('pokerhands.csv', 'r')
    for line in f:
        if line != '':
            hand_class_order.append(line.strip())
    f.close()

    load_probability_cache()

    file_list = glob.glob('*.txt')

    print "WinningHand,NumWinners,FavouredHand,UnfavouredHand,FavouredHandClass,UnfavouredHandClass,FavouredWon,P(FavouredWins),P(FavouredLoses),P(Tie),P(ThisOutcome),Sum(Ps),AllHands"
    for filename in file_list:
        f = open(filename, 'r')

        in_opening = False
        in_resolution = False
        hand_of_interest = False
        someone_all_in = False
        someone_calls = False
        hands = []
        winning_hand = ''
        winners = 0

        for line in f:
            if re.search(r"\*\*\* HOLE CARDS \*\*\*", line):
                in_opening = True
                in_resolution = False

            if in_opening and re.search(r"all in", line) and not re.search(r":", line):
                if someone_all_in:
                    hand_of_interest = True
                someone_all_in = True

            if in_opening and re.search(r"calls", line) and not re.search(r":", line):
                if someone_all_in:
                    someone_calls = True

            if re.search(r"\*\*\* FLOP \*\*\*", line):
                if someone_all_in and someone_calls:
                    hand_of_interest = True
                in_opening = False

            if re.search(r"\*\*\* SUMMARY \*\*\*", line):
                in_opening = False
                if someone_all_in and someone_calls:
                    hand_of_interest = True
                in_resolution = True

            if re.search(r"Full Tilt Poker Game", line):
                # Evaluate this hand
                if hand_of_interest and len(hands) == 2:
                    evaluate_result(hands, winners, winning_hand)
                in_opening = False
                in_resolution = False
                hand_of_interest = False
                someone_all_in = False
                someone_calls = False
                hands = []
                winning_hand = ''
                winners = 0

            if in_resolution and re.search(r"\[(\w\w \w\w)\]", line):
                matchdata = re.search(r"\[(\w\w \w\w)\]", line)
                hand = matchdata.group(1)
                hands.append(hand)
                if re.search(r"won", line):
                    winning_hand = hand
                    winners += 1

        # Parse last hand
        if hand_of_interest and len(hands) == 2:
            evaluate_result(hands, winners, winning_hand)

        f.close()

    save_probability_cache()

if __name__ == "__main__":
    main()
