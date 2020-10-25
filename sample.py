from wuggy.generators.wuggygenerator import WuggyGenerator

g = WuggyGenerator()
g.load("orthographic_english")
for w in g.generate_classic(["trumpet", "car", "child", "monster"]):
    print(w)