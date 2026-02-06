
def calc_n_primes(n):
    factors = [2]
    current = 3
    while (len(factors) < n):
        for i in factors:
            if i == factors[-1] and current % i != 0:
                factors.append(current)
                break
            elif current % i == 0:
                break
                
        current += 1
    return factors[-1]

if __name__ == "__main__":
    n = int(input("Enter n:\n"))
    print(f"{n}th prime is {calc_n_primes(n)}")   
            