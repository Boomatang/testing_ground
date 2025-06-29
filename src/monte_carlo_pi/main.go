package main

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"runtime"
	"strconv"
	"sync"
	"time"
)

type Result struct {
	Language string  `json:"language"`
	Format   string  `json:"format"`
	Time     int     `json:"time"` // or time.Duration/string depending on what `end` is
	Cores    int     `json:"cores"`
	Sample   int     `json:"sample"`
	Pi       float64 `json:"pi"`
}

func main() {
	// Get the number of samples from the command line arguments
	if len(os.Args) < 3 {
		fmt.Println("Usage: go run main.go single|multi <number_of_samples>")
		return
	}

	numSamples, err := strconv.Atoi(os.Args[2])
	if err != nil {
		fmt.Println("Error: Invalid number of samples provided.", err)
		return
	}

	var result Result
	if os.Args[1] == "single" {
		start := time.Now()
		piEstimate := monteCarloPi(numSamples)
		elapsed := time.Since(start)

		result = Result{Language: "golang", Format: "single threaded", Cores: 1, Sample: numSamples, Pi: piEstimate, Time: int(elapsed.Nanoseconds())}
	} else if os.Args[1] == "multi" {
		start := time.Now()
		piEstimate := monteCarloPiConcurrent(numSamples)
		elapsed := time.Since(start)
		result = Result{Language: "golang", Format: "multi threaded", Cores: runtime.NumCPU(), Sample: numSamples, Pi: piEstimate, Time: int(elapsed.Nanoseconds())}
	} else {
		fmt.Println("unsupport runtime used")
		return
	}
	jsonData, err := json.Marshal(result)
	if err != nil {
		panic(err)
	}
	fmt.Println(string(jsonData))
}

func monteCarloPi(numSamples int) float64 {
	var insideCircle int
	// Seed the random number generator
	s1 := rand.NewSource(time.Now().UnixNano())
	r1 := rand.New(s1)

	for i := 0; i < numSamples; i++ {
		x := r1.Float64()*2 - 1 // Generates a random float64 between 0.0 and 1.0
		y := r1.Float64()*2 - 1 // Generates a random float64 between 0.0 and 1.0

		// Check if the point (x, y) is inside the unit circle
		if (x*x + y*y) < 1.0 {
			insideCircle++
		}
	}

	return 4.0 * float64(insideCircle) / float64(numSamples)
}

func monteCarloPiWorker(numSamples int, seed int64, results chan<- int) {
	var insideCircle int
	r := rand.New(rand.NewSource(seed))

	for i := 0; i < numSamples; i++ {
		x := r.Float64()*2 - 1
		y := r.Float64()*2 - 1

		// Using x*x instead of math.Pow for better performance
		if (x*x + y*y) < 1.0 {
			insideCircle++
		}
	}

	results <- insideCircle
}

// monteCarloPiConcurrent estimates Pi using concurrent Monte Carlo method
func monteCarloPiConcurrent(numSamples int) float64 {
	numWorkers := runtime.NumCPU()
	samplesPerWorker := numSamples / numWorkers
	remainder := numSamples % numWorkers

	results := make(chan int, numWorkers)
	var wg sync.WaitGroup

	// Start workers
	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()

			// Distribute remainder samples among first few workers
			samples := samplesPerWorker
			if workerID < remainder {
				samples++
			}

			// Use different seeds for each worker to avoid correlation
			seed := time.Now().UnixNano() + int64(workerID*1000)
			monteCarloPiWorker(samples, seed, results)
		}(i)
	}

	// Close results channel when all workers are done
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	totalInsideCircle := 0
	for count := range results {
		totalInsideCircle += count
	}

	return 4.0 * float64(totalInsideCircle) / float64(numSamples)
}
