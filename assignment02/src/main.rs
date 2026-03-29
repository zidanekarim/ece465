/*
Dining Philosophers Problem: Restrictions that a philosopher may only pick up a fork when two forks are available; 
otherwise they will continue to do nothing. 
*/
use rand::Rng;

enum STATUS {
    thinking, 
    eating,
    hungry,
}

struct Philosopher {
    left_fork : bool, // 
    right_fork : bool,
    status : STATUS,
}

fn eat(index : i32, arr : [&Philosopher; 5]) {

}


fn main() {
    let mut philosophers: Vec<Philosopher> = Vec::new();

    for _ in 0..5 {
        let philosopher = Philosopher {
            left_fork: true,
            right_fork: false,
            status: STATUS::Thinking, //hmmm.,.. thinking
        };
        philosophers.push(philosopher);
    }
    


}
