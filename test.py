x = 0

def a():
    global x
    x += 1
    print(x)
    return True if x < 10 else False

while a():
    pass