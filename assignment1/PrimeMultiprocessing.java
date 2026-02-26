import java.util.Scanner;
import java.util.stream.IntStream;

public class PrimeMultiprocessing {

    public static void main(String[] args) {
        try (Scanner input = new Scanner(System.in)) {
            System.out.println("Enter desired prime:\n");
            if (input.hasNextInt()) {
                int n = input.nextInt();
                if (n > 0) {
                    System.out.println(String.format("The %dth prime is %d", n, countPrimes(n)));
                } else {
                    System.out.println("Please enter a positive integer.");
                }
            }
        }
    }

    public static int countPrimes(int n) {
        if (n == 1) return 2;
        
        // 1. Calculate a Safe Upper Limit
        // The Nth prime is approximately n * log(n). 
        // We multiply by a buffer to ensure the Nth prime is definitely inside this range.
        int limit = (int) (n * 2.5 * Math.log(n + 2)); // Safe estimation
        
        // 2. Use 'range' (which splits perfectly across cores)
        return IntStream.range(2, limit)
                .parallel()                 // Activate all cores
                .filter(PrimeMultiprocessing::isPrime)     // Keep only primes
                .skip(n - 1)                // Skip the first n-1 primes
                .findFirst()                // The next one is our answer
                .getAsInt();
    }

    public static boolean isPrime(int num) {
        if (num < 2) return false;
        // Optimization: Check only up to sqrt(num)
        for (int i = 2; i * i <= num; i++) {
            if (num % i == 0) return false;
        }
        return true;
    }
}