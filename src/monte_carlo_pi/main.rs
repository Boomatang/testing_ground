use num_cpus;
use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json;
use std::env;
use std::sync::mpsc;
use std::thread;
use std::time::Instant;

#[derive(Serialize, Deserialize, Debug)]
struct BenchmarkResult {
    language: String,
    format: String,
    time: u128,
    cores: usize,
    sample: u64,
    pi: f64,
}

fn main() {
    let args: Vec<String> = env::args().collect();

    let command = &args[1];

    let n_sample_string = &args[2];
    let n_sample = n_sample_string.parse::<u64>().unwrap();

    if command == "single" {
        let now = Instant::now();
        let result_pi = monte_carlo_pi(n_sample);
        let elapsed = now.elapsed();
        let result = BenchmarkResult {
            language: "rust".to_string(),
            format: "single threaded".to_string(),
            time: elapsed.as_nanos(),
            cores: 1,
            sample: n_sample,
            pi: result_pi,
        };
        let json_string = serde_json::to_string(&result).unwrap();
        println!("{}", json_string);
    } else if command == "multi" {
        let cores = num_cpus::get();
        let now = Instant::now();
        let result_pi = monte_carlo_pi_threaded(n_sample, cores);
        let elapsed = now.elapsed();
        let result = BenchmarkResult {
            language: "rust".to_string(),
            format: "multi threaded".to_string(),
            time: elapsed.as_nanos(),
            cores: cores,
            sample: n_sample,
            pi: result_pi,
        };
        let json_string = serde_json::to_string(&result).unwrap();
        println!("{}", json_string);
    } else {
        println!("command not found")
    }
}

fn monte_carlo_pi(sample: u64) -> f64 {
    let mut acc: f64 = 0.0;
    let mut rng = rand::rng();
    for _ in 1..sample {
        let x = rng.random_range(-1.0..=1.0);
        let y = rng.random_range(-1.0..=1.0);
        if (x * x + y * y) <= 1.0 {
            acc += 1.0
        }
    }

    let float_sample: f64 = sample as f64;
    return 4.0 * acc / float_sample;
}

fn monte_carlo_pi_threaded(sample: u64, cores: usize) -> f64 {
    let count: u64 = cores.try_into().unwrap();
    let block = sample / count;

    let (tx, rx) = mpsc::channel();

    let mut handles = vec![];
    for _ in 0..cores {
        let tx = tx.clone();
        let handle = thread::spawn(move || {
            let mut acc: f64 = 0.0;
            let mut rng = rand::rng();
            for _ in 1..block {
                let x = rng.random_range(-1.0..=1.0);
                let y = rng.random_range(-1.0..=1.0);
                if (x * x + y * y) <= 1.0 {
                    acc += 1.0
                }
            }
            let _ = tx.send(acc);
        });
        handles.push(handle);
    }

    drop(tx);
    // let mut acc_results: Vec<f64> = Vec::new();
    //
    // for result in rx {
    //     acc_results.push(result);
    // }

    for handle in handles {
        handle.join().unwrap();
    }

    let acc_results: Vec<f64> = rx.iter().collect();
    let acc: f64 = acc_results.iter().sum();

    let float_sample: f64 = sample as f64;
    return 4.0 * acc / float_sample;
}
