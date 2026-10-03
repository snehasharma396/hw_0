import random
import sys

if len(sys.argv) != 2:
    print(f"Usage: python3 {sys.argv[0]} filename", file=sys.stderr)
    sys.exit(1)

filename = sys.argv[1]

with open(filename, encoding="utf-8") as source:
    for line in source:
        if random.random() < 0.01:
            print(line, end="")
