import multiprocessing
import math


def is_prime(num):
    if num < 2:
        return None
    for i in range(2, int(math.sqrt(num)) + 1):
        if num % i == 0:
            return None 
    return num 

def calc_n_primes_parallel(n):
    factors = [2]
    current = 3
    batch_size = 25000  
    
    with multiprocessing.Pool() as pool:
        while len(factors) < n:

            candidates = range(current, current + batch_size)

            results = pool.map(is_prime, candidates)
            for res in results:
                if res is not None:
                    factors.append(res)
                    if len(factors) == n:
                        return factors[-1]
            
            current += batch_size
            
    return factors[-1]

if __name__ == "__main__":
    try:
        user_input = input("Enter n:\n")
        n = int(user_input)
        
        if n < 1:
            print("Please enter a positive integer.")
        elif n == 1:
            print(f"1st prime is 2")
        else:
            result = calc_n_primes_parallel(n)
            print(f"{n}th prime is {result}")
            
    except ValueError:
        print("Invalid input. Please enter an integer.")