def repeat(n:int, music:str) -> str:
    for i in range (n):
        if music == "":
            result = "Not music defined"
        else:
            result = f" The song {music} was put on radio {i+1} times"
    return result

def main():
    print (repeat(2, 'afrobeat'))

if __name__ == '__main__':
    main()
