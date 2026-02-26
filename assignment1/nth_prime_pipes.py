import multiprocessing
import math

def worker(child_conn):
    while True:
        msg = child_conn.recv() 
        
        if msg == 'STOP':
            break 
            
        start, end = msg
        primes = []
        for num in range(start, end):
            if num < 2:
                continue
            is_p = True
            for i in range(2, int(math.sqrt(num)) + 1):
                if num % i == 0:
                    is_p = False
                    break
            if is_p:
                primes.append(num)
                
        child_conn.send(primes) 

def calc_n_primes_pipe(n):
    num_workers = multiprocessing.cpu_count()

    pipes = [multiprocessing.Pipe() for _ in range(num_workers)]
    parent_conns = [p[0] for p in pipes]
    child_conns = [p[1] for p in pipes]
    
    workers = []
    for child_conn in child_conns:
        p = multiprocessing.Process(target=worker, args=(child_conn,))
        p.start()
        workers.append(p)
        
    primes = [2]
    current = 3
    chunk_size = 25000  
    
    try:
        while len(primes) < n:
            for parent_conn in parent_conns:
                parent_conn.send((current, current + chunk_size))
                current += chunk_size

            for parent_conn in parent_conns:
                batch_primes = parent_conn.recv()
                primes.extend(batch_primes)
                
    finally:
        for parent_conn in parent_conns:
            parent_conn.send('STOP')
        for p in workers:
            p.join()

    return primes[n - 1]

if __name__ == "__main__":
    try:
        user_input = input("Enter n:\n")
        n = int(user_input)
        
        if n < 1:
            print("Please enter a positive integer.")
        elif n == 1:
            print("1st prime is 2")
        else:
            result = calc_n_primes_pipe(n)
            print(f"{n}th prime is {result}")
            
    except ValueError:
        print("Invalid input. Please enter an integer.")