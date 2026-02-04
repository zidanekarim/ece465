import java.util.Scanner;
import java.util.List;
import java.util.ArrayList;


public class Prime {

    public static void main(String[] args) {
        Scanner input = new Scanner(System.in);
        System.out.println("Enter desired prime:\n");
        int n = input.nextInt();
        String output = String.format("The %dth prime is %d", n, countPrimes(n));
        System.out.println(output);
        input.close();
    }

    

    public static int countPrimes(int n) {
        List<Integer> factors = new ArrayList<Integer>();
            factors.add(2);
            int current = 3;
            while (factors.size()<n) {
                if (!factors.contains(current)) {
                    for (int i: factors) {
                        if (i == factors.get(factors.size()-1) && current % i != 0) {
                            factors.add(current);
                            break;
                        }
                        else if (current % i == 0) {
                            break;
                        }
                    }
                    current++;
                }
            }
            return factors.get(factors.size()-1);
    }
}