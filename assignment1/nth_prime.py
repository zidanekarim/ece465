

def calc_n_primes(n):
    factors = [2]
    current = 3
    while (len(factors) < n):
        prime = False
        if current not in factors:
            for i in factors:
                if i == factors[-1] and current % i != 0:
                    prime = True
                    break
                elif current % i == 0:
                    break
            if prime:
                factors.append(current)
        current += 1
    return factors[-1]

if __name__ == "__main__":
    n = int(input("Enter n:\n"))
    print(f"{n}th prime is {calc_n_primes(n)}")   
            