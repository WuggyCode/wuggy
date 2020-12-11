from wuggy import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for w in g.generate_classic(["trumpet"]):
    print(w)
