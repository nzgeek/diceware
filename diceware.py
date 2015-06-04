import argparse, os, re
from collections import namedtuple

##############################################################################


class Dice(object):
    '''
    Represents a dice that can be rolled to get a random value.
    '''
    def __init__(self, num_sides=6):
        '''
        Creates a new dice.
        @param num_sides: The number of sides on the dice (2..20).
        @param values: The values on each side of the dice.
        '''
        # Check and set the number of sides.
        assert(num_sides >= 2 and num_sides <= 20)
        self.num_sides = int(num_sides)
        # There are 256 possible random values (0..255). In order to generate
        # an even distribution of values, we need to range to be 0..N, where
        # N+1 is cleanly divisible by num_sides. Any values greater than N
        # will be ignored and a new random value generated.
        # In order to avoid throwing too many values away, we'll choose the
        # largest value of N that fits in the range.
        divisor = int(256 / self.num_sides)
        self.ceiling = (divisor * self.num_sides) - 1

    def roll(self):
        '''
        Returns a random number, generated as if the user had rolled a dice
        with a specified number of sides.
        '''
        # Find the next random value that's in the range 0..ceiling.
        random = os.urandom(1)[0]
        while random > self.ceiling:
            random = os.urandom(1)[0]
        # Find which side (0-based) was rolled, then add 1.
        side = random % self.num_sides
        return side + 1


##############################################################################


DicewarePassword = namedtuple('DicewarePassword', ['rolls', 'words'])


class DicewareWordListException(RuntimeError):
    pass


class DicewareWordList(object):
    DEFAULT_DICE_SIDES = 6
    DEFAULT_NUM_DICE = 5
    PARSE_OPTION = re.compile(r'^(D(?:ICE)|S(?:IDES))\s*[=:]\s*(\d+)$', re.I)
    PARSE_WORD = re.compile(r'^(\d+)\s+(.*?)$')
    
    dice_sides = DEFAULT_DICE_SIDES
    num_dice = DEFAULT_NUM_DICE
    dice = None
    words = None
    
    def load(self, wordlist):
        # Prepare for the load.
        self.words = {}
        found_words = False
        
        # Parse each line, looking for important values.
        for line in wordlist:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Check if we've matched a word entry.
            match = self.PARSE_WORD.match(line)
            if match:
                found_words = True
                roll = match.group(1)
                if self._is_valid_roll(roll):
                    self.words[roll] = match.group(2)
            # If we haven't found any word entries yet, check for 
            if not found_words:
                match = self.PARSE_OPTION.match(line)
                if match:
                    opt = match.group(1).upper()
                    value = int(match.group(2))
                    if opt[0] == 'D':
                        self.num_dice = value
                    elif opt[0] == 'S':
                        self.dice_sides = value

        # Generate a dice with the correct number of sides.
        self.dice = Dice(self.dice_sides)
    
    def _is_valid_roll(self, roll):
        if len(roll) != self.num_dice:
            return False
        for dice_roll in list(roll):
            if not int(dice_roll) in range(1, self.dice_sides + 1):
                return False
        return True
    
    def verify(self):
        if not self.words:
            raise DicewareWordListException('No word list has been loaded.')
        self._verify('')
    
    def _verify(self, prefix):
        for side in range(1, self.dice_sides + 1):
            roll = prefix + str(side)
            if len(roll) == self.num_dice:
                if not self.words.get(roll, None):
                    raise DicewareWordListException('Word missing for dice roll "{0}".'.format(roll))
            else:
                self._verify(roll)
    
    def get_password(self, num_words):
        if not self.dice or not self.words:
            return DicewarePassword([], [])
    
        rolls = [self._roll_dice() for x in range(num_words)]
        words = [self.words.get(roll) for roll in rolls]
        return DicewarePassword(rolls, words)

    def _roll_dice(self):
        return ''.join(str(self.dice.roll()) for x in range(self.num_dice))


##############################################################################


parser = argparse.ArgumentParser('diceware.py',
                                 description='Generates a diceware password.')
parser.add_argument('--wordlist', '-l',
                    type=argparse.FileType('r'),
                    default='wordlist.txt',
                    help='The path to a file containing a diceware word list.',
                    metavar='<file>')
parser.add_argument('--words', '-w',
                    type=int,
                    default=5,
                    help='The number of words in each password.',
                    metavar='<number>')
parser.add_argument('--passwords', '-n',
                    type=int,
                    default=1,
                    help='The number of passwords to generate.',
                    metavar='<number>')
parser.add_argument('--showrolls', '-r',
                    action='store_true',
                    default=False,
                    help='If present, the dice rolls will also be displayed.')
parser.add_argument('--out', '-o',
                    type=argparse.FileType('w'),
                    help='Write the password list to a file instead of stdout.',
                    metavar='<file>')
args = parser.parse_args()


##############################################################################


# Load and verify the word list.
wordlist = DicewareWordList()
try:
    wordlist.load(args.wordlist)
    wordlist.verify()
except DicewareWordListException as ex:
    print(str(ex))
    exit()


for x in range(args.passwords):
    password = wordlist.get_password(args.words)
    
    line = []
    if args.showrolls:
        line.append(' '.join(password.rolls))
    line.append(' '.join(password.words))
    
    if args.out:
        args.out.write('\t'.join(line))
        args.out.write('\n')
    else:
        print('\t'.join(line))

if args.out:
    args.out.flush()
